"""Build exact native SVG vectors and a portable trigger state machine."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from openrive_sync import tracks

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('svg_rml', ROOT.parent/'co/tools/build_co.py')
svg_rml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svg_rml)
add, geometry = svg_rml.add, svg_rml.path_geometry


def build():
    out = ROOT/'source'
    qa = ROOT/'verification'
    out.mkdir(exist_ok=True)
    qa.mkdir(exist_ok=True)
    svg = ET.parse(ROOT/'contho914x880.svg').getroot()
    elements = list(svg)
    definitions = {e.get('id'): e for e in svg.iter() if e.get('id')}
    root = ET.Element('Rive', version='1', kind='fragment')
    art = add(root, 'Artboard', name='Rabbit', width=914, height=1100, clip='true')
    style = add(art, 'LayoutComponentStyle', name='Jump headroom')
    art.set('styleId', style.get('id'))
    rabbit = add(art, 'Node', name='RabbitRoot', x=520, y=1044)
    coords = add(rabbit, 'Node', name='SVGCoordinates', x=-520, y=-824)
    head = add(coords, 'Node', name='Head', x=377, y=465)
    head_coords = add(head, 'Node', name='HeadCoordinates', x=-377, y=-465)

    def convert(parent, element, name, clips=()):
        tag = element.tag.split('}')[-1]
        if tag == 'g':
            group = add(parent, 'Node', name=name)
            mask = element.get('mask')
            if mask:
                shape = add(group, 'Shape', name=name+' clip')
                for e in definitions[mask[5:-1]]:
                    geometry(shape, e.get('d'))
                clips = clips+(shape.get('id'),)
            for j, e in reversed(list(enumerate(element))):
                convert(group, e, name+f' {j}', clips)
        elif tag == 'path':
            shape = add(parent, 'Shape', name=name)
            geometry(shape, element.get('d'))
            svg_rml.color(add(shape, 'Fill', fillRule='nonZero'), element.get('fill'))
            for clip in clips:
                add(shape, 'ClippingShape', sourceId=clip)

    # Keep the source painter order, including all three SVG masks.
    convert(head_coords, elements[13], 'Cheek contour')
    eye = add(head_coords, 'Node', name='Eye', x=321, y=381)
    eye_coords = add(eye, 'Node', name='EyeCoordinates', x=-321, y=-381)
    convert(eye_coords, elements[12], 'Pupil')
    convert(eye_coords, elements[10], 'Eye white')
    front = add(head_coords, 'Node', name='FrontEar', x=421, y=322)
    front_coords = add(front, 'Node', name='FrontEarCoordinates', x=-421, y=-322)
    convert(front_coords, elements[9], 'Inner front ear')
    convert(front_coords, elements[8], 'Front ear silhouette')
    convert(head_coords, elements[7], 'Muzzle and nose')
    convert(head_coords, elements[5], 'Head silhouette')
    rear = add(head_coords, 'Node', name='RearEar', x=382, y=312)
    rear_coords = add(rear, 'Node', name='RearEarCoordinates', x=-382, y=-312)
    convert(rear_coords, elements[4], 'Rear ear silhouette')
    body = add(coords, 'Node', name='Body')
    convert(body, elements[3], 'Leg contours')
    convert(body, elements[1], 'Body silhouette')
    tail = add(coords, 'Node', name='Tail', x=764, y=699)
    tail_coords = add(tail, 'Node', name='TailCoordinates', x=-764, y=-699)
    convert(tail_coords, elements[0], 'Tail silhouette')

    idle = add(art, 'LinearAnimation', name='idle', fps=60, duration=60, loopValue='loop')
    jump = add(art, 'LinearAnimation', name='jump', fps=60, duration=84, loopValue='oneShot')
    # Keep a complete offline source equivalent to the keys authored through MCP.
    animated_nodes = {e.get('name'):e for e in art.iter() if e.get('name')}
    for (name, prop), values in tracks().items():
        target = animated_nodes[name]
        if prop == 'rotationDegrees':
            prop = 'rotation'
            values = [v*svg_rml.math.pi/180 for v in values]
        svg_rml.key(jump, target, prop, list(enumerate(values)))
        svg_rml.key(idle, target, prop, [(0,values[0]),(60,values[0])])
    sm = add(art, 'StateMachine', name='RabbitController')
    art.set('defaultStateMachineId', sm.get('id'))
    trigger = add(sm, 'StateMachineTrigger', name='jump')
    reset = add(sm, 'StateMachineTrigger', name='reset')
    layer = add(sm, 'StateMachineLayer', name='Rabbit movement')
    any_state = add(layer, 'AnyState', x=-200, y=-150)
    add(layer, 'ExitState', x=700, y=-150)
    entry = add(layer, 'EntryState', x=-200, y=0)
    standing = add(layer, 'AnimationState', animationId=idle.get('id'), reset='true', x=40, y=0)
    jumping = add(layer, 'AnimationState', animationId=jump.get('id'), reset='true', x=340, y=0)
    add(entry, 'StateTransition', stateToId=standing.get('id'), duration=0)
    transition = add(standing, 'StateTransition', stateToId=jumping.get('id'), duration=0)
    add(transition, 'TransitionTriggerCondition', inputId=trigger.get('id'))
    add(jumping, 'StateTransition', stateToId=standing.get('id'), duration=0,
        enableExitTime='true', exitTimeIsPercetange='true', exitTime=100)
    transition = add(any_state, 'StateTransition', stateToId=standing.get('id'), duration=60)
    add(transition, 'TransitionTriggerCondition', inputId=reset.get('id'))
    art.remove(sm)
    art.insert(list(art).index(idle), sm)
    ET.indent(root)
    (out/'scene.rml').write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    (out/'rive.yaml').write_text('name: rabbit_jump\nmain: Rabbit\nartboard:\n  width: 914\n  height: 1100\n')
    cli = str(Path.home()/'.rive/bin/rive.exe')
    for flags, name in [(['--verify','--format=json'], 'rive_verify.json'), (['--once','--format=json'], 'rive_build.json')]:
        p = subprocess.run([cli, str(out), *flags], capture_output=True, text=True, encoding='utf8')
        (qa/name).write_text(p.stdout, encoding='utf8')
        if p.returncode:
            raise RuntimeError(p.stdout+p.stderr)
    shutil.copyfile(out/'build/rabbit_jump.riv', ROOT/'rabbit_jump.riv')
    (qa/'source_manifest.json').write_text(json.dumps({
        'source_sha256': hashlib.sha256((ROOT/'contho914x880.svg').read_bytes()).hexdigest(),
        'canvas': [914,1100], 'source_offset': [0,220], 'native_vectors': True,
        'svg_masks_preserved': 3, 'jump_seconds': 1.4,
        'note': 'Native source mirrors the animation keys authored through OpenRive MCP.'
    }, indent=2))
    print('Built native rabbit artwork and controller')


if __name__ == '__main__':
    build()
