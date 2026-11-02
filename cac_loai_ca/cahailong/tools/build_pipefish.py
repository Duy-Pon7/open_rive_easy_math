"""Preserve the original rigid pipefish vectors; author locomotion via OpenRive MCP."""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SOURCE = ROOT.parent/'cahailong.svg'
WIDTH, HEIGHT = 335, 81
OFFSET = (24, 28)
PIVOT = (143.5, 12.5)
FRAMES = 120
spec = importlib.util.spec_from_file_location('vectors', REPO/'co/tools/build_co.py')
vec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vec)
sys.path.insert(0, str(REPO/'loa_doc/tools'))
from mcp_client import OpenRive


def motion():
    result = {}
    for f in range(0, FRAMES+1, 2):
        t = 2*math.pi*f/FRAMES
        values = {
            ('FishRoot','x'): OFFSET[0]+PIVOT[0]+2.5*math.sin(t),
            ('FishRoot','y'): OFFSET[1]+PIVOT[1]+1.15*math.sin(t),
            ('FishRoot','rotationDegrees'): .3*math.sin(t),
            ('PectoralFin','rotationDegrees'): 13*math.sin(5*t),
            ('PectoralFin','scaleY'): .84+.16*math.cos(5*t),
        }
        for key, value in values.items():
            result.setdefault(key, []).append((f, round(value, 8)))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:56545')
    args = parser.parse_args()
    source = ROOT/'source'; qa = ROOT/'verification'
    source.mkdir(parents=True, exist_ok=True); qa.mkdir(exist_ok=True)
    svg = ET.parse(SOURCE).getroot()
    definitions = {e.get('id'):e for e in svg.iter() if e.get('id')}
    add = vec.add
    root = ET.Element('Rive', version='1', kind='fragment')
    art = add(root, 'Artboard', name='Ca Hai Long', width=WIDTH, height=HEIGHT, clip='true')
    style = add(art, 'LayoutComponentStyle', name='Transparent canvas')
    art.set('styleId', style.get('id'))
    rig = add(art, 'Node', name='FishRoot', x=OFFSET[0]+PIVOT[0], y=OFFSET[1]+PIVOT[1])
    coords = add(rig, 'Node', name='OriginalSVGCoordinates', x=-PIVOT[0], y=-PIVOT[1])

    def convert(parent, element, name, clips=()):
        tag = element.tag.split('}')[-1]
        if tag in ('mask','defs'):
            return
        if tag == 'g':
            group = add(parent, 'Node', name=name)
            if element.get('mask'):
                mask = definitions[element.get('mask')[5:-1]]
                clipper = add(group, 'Shape', name='Rigid body shading mask')
                for child in mask:
                    vec.path_geometry(clipper, child.get('d'))
                clips += (clipper.get('id'),)
            for i, child in reversed(list(enumerate(element))):
                convert(group, child, f'{name}.{i}', clips)
            return
        assert tag == 'path'
        if name == 'Pectoral fin':
            pivot = add(parent, 'Node', name='PectoralFin', x=216, y=14)
            parent = add(pivot, 'Node', name='OriginalFinCoordinates', x=-216, y=-14)
        shape = add(parent, 'Shape', name=name)
        vec.path_geometry(shape, element.get('d'))
        if element.get('fill', 'none') != 'none':
            vec.color(add(shape, 'Fill', fillRule='nonZero'), element.get('fill'))
        if element.get('stroke'):
            stroke = add(shape, 'Stroke', thickness=element.get('stroke-width',1), cap=element.get('stroke-linecap','butt'), join='miter')
            vec.color(stroke, element.get('stroke'))
        for clip in clips:
            add(shape, 'ClippingShape', sourceId=clip)

    labels = {0:'Rigid body and tail', 2:'Body shading and markings', 3:'Pectoral fin', 4:'Eye white', 5:'Pupil', 6:'Mouth outline', 7:'Mouth shading'}
    for i, element in reversed(list(enumerate(svg))):
        convert(coords, element, labels.get(i, f'SVG {i}'))
    idle = add(art, 'LinearAnimation', name='idle', fps=60, duration=60, loopValue='loop')
    swim = add(art, 'LinearAnimation', name='swim', fps=60, duration=FRAMES, loopValue='loop')
    for animation, frames in [(idle,60),(swim,FRAMES)]:
        vec.key(animation, rig, 'x', [(0,OFFSET[0]+PIVOT[0]),(frames,OFFSET[0]+PIVOT[0])])
    sm = add(art, 'StateMachine', name='CaHaiLongController')
    art.set('defaultStateMachineId', sm.get('id'))
    swimming = add(sm, 'StateMachineBool', name='is_swimming', value='false')
    layer = add(sm, 'StateMachineLayer', name='Locomotion')
    add(layer, 'AnyState', x=-200, y=-150);add(layer, 'ExitState', x=650, y=-150)
    entry = add(layer, 'EntryState', x=-200, y=0)
    rest = add(layer, 'AnimationState', animationId=idle.get('id'), reset='true', x=40, y=0)
    moving = add(layer, 'AnimationState', animationId=swim.get('id'), reset='true', x=340, y=0)
    add(entry, 'StateTransition', stateToId=rest.get('id'), duration=0)
    for start, end, op in [(rest,moving,'equal'),(moving,rest,'notEqual')]:
        transition = add(start, 'StateTransition', stateToId=end.get('id'), duration=200, enableEarlyExit='true')
        add(transition, 'TransitionBoolCondition', inputId=swimming.get('id'), opValue=op)
    art.remove(sm);art.insert(list(art).index(idle),sm)
    ET.indent(root)
    (source/'scene.rml').write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    (source/'rive.yaml').write_text(f'name: cahailong\nmain: Ca Hai Long\nartboard:\n  width: {WIDTH}\n  height: {HEIGHT}\n')
    cli = str(Path.home()/'.rive/bin/rive.exe')
    for flags, filename in [(['--verify','--format=json'],'rive_verify.json'),(['--once','--format=json'],'rive_build.json')]:
        result = subprocess.run([cli,str(source),*flags],capture_output=True,text=True,encoding='utf8')
        (qa/filename).write_text(result.stdout,encoding='utf8')
        if result.returncode:
            raise RuntimeError(result.stdout+result.stderr)
    client = OpenRive(args.base)
    meta_path = ROOT/'openrive.json'
    local = source/'build/cahailong.riv'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text());project = meta['project_id']
    else:
        result = client.call('import_riv',dict(name='Ca Hai Long - Rigid Body Swim',dataBase64=base64.b64encode(local.read_bytes()).decode()))
        project = result.get('id') or result.get('projectId') or result.get('project',{}).get('id')
        assert project,result
    meta = dict(project_id=project,base_url=args.base,editor_url=args.base+'/editor/'+project)
    meta_path.write_text(json.dumps(meta,indent=2))
    baseline = {('FishRoot','x'):OFFSET[0]+PIVOT[0],('FishRoot','y'):OFFSET[1]+PIVOT[1],('FishRoot','rotationDegrees'):0,('PectoralFin','rotationDegrees'):0,('PectoralFin','scaleY'):1}
    ops = []
    for (obj,prop),samples in motion().items():
        for timeline, values in [('swim',samples),('idle',[(0,baseline[obj,prop]),(60,baseline[obj,prop])])]:
            ops.append(dict(op='add_keyframes',timeline=timeline,object=obj,property=prop,keys=[dict(frame=f,value=v,ease='linear') for f,v in values]))
    result = client.call('apply_edit_plan',dict(project=project,operations=ops))
    (qa/'animation-mcp.json').write_text(json.dumps(result,indent=2))
    for tool,filename in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result = client.call(tool,dict(project=project))
        (qa/filename).write_text(json.dumps(result,indent=2))
        if tool == 'diagnose_project':
            assert result['valid'],result
            print(json.dumps(result),flush=True)
    result = client.call('export_riv',dict(project=project))
    data = base64.b64decode(result['dataBase64'])
    (ROOT/'cahailong.riv').write_bytes(data)
    doc = client.snapshot(project)['doc']
    (ROOT/'openrive-project.json').write_text(json.dumps(doc,indent=2))
    (qa/'manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),rive_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),canvas=[WIDTH,HEIGHT],svg_offset=OFFSET,loop_seconds=FRAMES/60,rigid_body=True,animated_nodes=['FishRoot','PectoralFin']),indent=2))
    runtime = ROOT/'runtime';runtime.mkdir(exist_ok=True)
    for name in ['canvas_advanced.mjs','rive.wasm','rive_fallback.wasm','package.json']:
        shutil.copyfile(REPO/'fish/runtime'/name,runtime/name)
    print(meta['editor_url'],flush=True)


if __name__ == '__main__':
    main()
