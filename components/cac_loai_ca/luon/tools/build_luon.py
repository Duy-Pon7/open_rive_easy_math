"""Build the supplied eel as editable native Rive vectors, then import via MCP."""
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

import numpy as np
from svgpathtools import CubicBezier, Line, Path as SvgPath, parse_path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'luon.svg'
FRAMES = 96
WIDTH, HEIGHT = 351, 146
OFFSET = (32, 48)
spec = importlib.util.spec_from_file_location('vectors', REPO / 'co/tools/build_co.py')
vec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vec)
sys.path.insert(0, str(REPO / 'loa_doc/tools'))
from mcp_client import OpenRive


def subdivide(data):
    pieces = []
    for segment in parse_path(data):
        assert isinstance(segment, (CubicBezier, Line))
        span = abs(segment.end - segment.start)
        if isinstance(segment, CubicBezier):
            span = max(span, abs(segment.control1-segment.start), abs(segment.control2-segment.end))
        n = max(1, math.ceil(span / 10))
        for i in range(n):
            part = segment.cropped(i/n, (i+1)/n)
            start = pieces[-1].end if pieces else part.start
            end = segment.end if i == n-1 else part.end
            # Exact adjacency is essential: tiny floating point differences
            # otherwise turn one closed contour into many open subpaths.
            part = CubicBezier(start, part.control1, part.control2, end) if isinstance(part, CubicBezier) else Line(start, end)
            pieces.append(part)
    return SvgPath(*pieces).d()


def deformation(frame):
    """Head-to-tail wave; centerline arc length and normal thickness are preserved."""
    xs = np.arange(-40, 331, .25)
    u = np.maximum(0, (242-xs)/242)
    phase = 2*math.pi*(frame/FRAMES-1.1*u)
    wave = 18*u**1.5*np.sin(phase)
    slope = -18/242*(1.5*np.sqrt(u)*np.sin(phase)-2*math.pi*1.1*u**1.5*np.cos(phase))
    dx = np.sqrt(1-np.clip(slope, -.9, .9)**2)
    integral = np.r_[0, np.cumsum((dx[:-1]+dx[1:])*.125)]
    xmap = 270+integral-np.interp(270, xs, integral)

    def point(p):
        x, y = p.real, p.imag
        tangent_y = float(np.interp(x, xs, slope))
        tangent_x = math.sqrt(1-min(.9, abs(tangent_y))**2)
        return complex(float(np.interp(x, xs, xmap))-(y-29)*tangent_y,
                       29+float(np.interp(x, xs, wave))+(y-29)*tangent_x)
    return point


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:56545')
    args = parser.parse_args()
    source = ROOT/'source'; qa = ROOT/'verification'
    source.mkdir(exist_ok=True); qa.mkdir(exist_ok=True)
    svg = ET.parse(SOURCE).getroot()
    definitions = {e.get('id'):e for e in svg.iter() if e.get('id')}
    root = ET.Element('Rive', version='1', kind='fragment')
    add = vec.add
    art = add(root, 'Artboard', name='Ca Luon', width=WIDTH, height=HEIGHT, clip='true')
    style = add(art, 'LayoutComponentStyle', name='Transparent canvas with wave clearance')
    art.set('styleId', style.get('id'))
    coords = add(art, 'Node', name='EelRoot', x=OFFSET[0], y=OFFSET[1])
    vertices = []

    def geometry(shape, data, label):
        result = vec.path_geometry(shape, subdivide(data))
        for i, v in enumerate(result):
            v.set('name', f'{label} vertex {i}')
            p = complex(float(v.get('x')), float(v.get('y')))
            a = float(v.get('inDistance'))*complex(math.cos(float(v.get('inRotation'))), math.sin(float(v.get('inRotation'))))
            b = float(v.get('outDistance'))*complex(math.cos(float(v.get('outRotation'))), math.sin(float(v.get('outRotation'))))
            vertices.append((v, p, a, b))

    def convert(parent, element, label, clips=()):
        tag = element.tag.split('}')[-1]
        if tag in ('mask', 'defs'):
            return
        if tag == 'g':
            group = add(parent, 'Node', name=label)
            if element.get('mask'):
                mask = definitions[element.get('mask')[5:-1]]
                clip = add(group, 'Shape', name='Body shading mask')
                for child in mask:
                    geometry(clip, child.get('d'), 'Mask')
                clips += (clip.get('id'),)
            for i, child in reversed(list(enumerate(element))):
                convert(group, child, f'{label}.{i}', clips)
            return
        assert tag == 'path'
        if label == 'Pectoral fin':
            pivot = add(parent, 'Node', name='PectoralFin', x=235, y=27)
            parent = add(pivot, 'Node', name='FinCoordinates', x=-235, y=-27)
        shape = add(parent, 'Shape', name=label)
        geometry(shape, element.get('d'), label)
        if element.get('fill', 'none') != 'none':
            vec.color(add(shape, 'Fill', fillRule='nonZero'), element.get('fill'))
        if element.get('stroke'):
            vec.color(add(shape, 'Stroke', thickness=element.get('stroke-width', 1), cap='butt', join='miter'), element.get('stroke'))
        for clip in clips:
            add(shape, 'ClippingShape', sourceId=clip)

    labels = {0:'Body', 2:'Body shading', 3:'Pectoral fin', 4:'Eye white', 6:'Pupil'}
    for i, element in reversed(list(enumerate(svg))):
        convert(coords, element, labels.get(i, f'SVG {i}'))
    idle = add(art, 'LinearAnimation', name='idle', fps=60, duration=60, loopValue='loop')
    swim = add(art, 'LinearAnimation', name='swim', fps=60, duration=FRAMES, loopValue='loop')
    samples = list(range(0, FRAMES+1, 3))
    maps = [deformation(f) for f in samples]
    for v, p, a, b in vertices:
        values = []
        for transform in maps:
            q = transform(p)
            values.append(vec.vertex_values(q, transform(p+a)-q, transform(p+b)-q))
        for prop in ('x', 'y', 'inRotation', 'inDistance', 'outRotation', 'outDistance'):
            base = float(v.get(prop))
            vec.key(idle, v, prop, [(0, base), (60, base)])
            numbers = [float(value[prop]) for value in values]
            # Avoid angle wrapping across +/- pi during interpolation.
            if prop.endswith('Rotation'):
                numbers = np.unwrap(numbers).tolist()
                base += round((numbers[0]-base)/(2*math.pi))*2*math.pi
                v.set(prop, str(base))
                # Idle needs the same angular branch for smooth state blending.
                idle.findall('KeyedObject')[-1].find('KeyedProperty/KeyFrameDouble').set('value', str(base))
                idle.findall('KeyedObject')[-1].findall('KeyedProperty/KeyFrameDouble')[1].set('value', str(base))
            vec.key(swim, v, prop, list(zip(samples, numbers)))

    sm = add(art, 'StateMachine', name='CaLuonController')
    art.set('defaultStateMachineId', sm.get('id'))
    swimming = add(sm, 'StateMachineBool', name='is_swimming', value='false')
    layer = add(sm, 'StateMachineLayer', name='Locomotion')
    add(layer, 'AnyState', x=-200, y=-150); add(layer, 'ExitState', x=650, y=-150)
    entry = add(layer, 'EntryState', x=-200, y=0)
    rest = add(layer, 'AnimationState', animationId=idle.get('id'), reset='true', x=40, y=0)
    moving = add(layer, 'AnimationState', animationId=swim.get('id'), reset='true', x=340, y=0)
    add(entry, 'StateTransition', stateToId=rest.get('id'), duration=0)
    for start, end, op in ((rest, moving, 'equal'), (moving, rest, 'notEqual')):
        transition = add(start, 'StateTransition', stateToId=end.get('id'), duration=220, enableEarlyExit='true')
        add(transition, 'TransitionBoolCondition', inputId=swimming.get('id'), opValue=op)
    art.remove(sm); art.insert(list(art).index(idle), sm)
    ET.indent(root)
    (source/'scene.rml').write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    (source/'rive.yaml').write_text(f'name: luon\nmain: Ca Luon\nartboard:\n  width: {WIDTH}\n  height: {HEIGHT}\n')
    cli = str(Path.home()/'.rive/bin/rive.exe')
    for flags, filename in ((['--verify', '--format=json'], 'rive_verify.json'), (['--once', '--format=json'], 'rive_build.json')):
        result = subprocess.run([cli, str(source), *flags], capture_output=True, text=True, encoding='utf8')
        (qa/filename).write_text(result.stdout, encoding='utf8')
        if result.returncode:
            raise RuntimeError(result.stdout+result.stderr)
    local = source/'build/luon.riv'
    client = OpenRive(args.base)
    meta_path = ROOT/'openrive.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        project = meta['project_id']
        snapshot = client.snapshot(project)
        (qa/'before-rebuild.json').write_text(json.dumps(snapshot), encoding='utf8')
        created = client.call('import_riv', dict(name='Ca Luon rebuild staging', dataBase64=base64.b64encode(local.read_bytes()).decode()))
        staging = created.get('id') or created.get('projectId') or created.get('project', {}).get('id')
        assert staging, created
        doc = client.snapshot(staging)['doc']
        client.update(project, doc, snapshot['meta']['updatedAt'])
        client.call('delete_project', dict(project=staging))
    else:
        created = client.call('import_riv', dict(name='Ca Luon - Idle and Swim', dataBase64=base64.b64encode(local.read_bytes()).decode()))
        project = created.get('id') or created.get('projectId') or created.get('project', {}).get('id')
        assert project, created
    meta = dict(project_id=project, base_url=args.base, editor_url=args.base+'/editor/'+project)
    meta_path.write_text(json.dumps(meta, indent=2))
    ops = []
    for timeline, frames, amplitude in [('idle', 60, 0), ('swim', FRAMES, 5)]:
        ops.append(dict(op='add_keyframes', timeline=timeline, object='PectoralFin', property='rotationDegrees', keys=[dict(frame=f, value=amplitude*math.sin(4*math.pi*f/frames), ease='linear') for f in range(0, frames+1, 3)]))
    result = client.call('apply_edit_plan', dict(project=project, operations=ops))
    (qa/'fin-keyframes-mcp.json').write_text(json.dumps(result, indent=2))
    for tool, name in [('get_project', 'openrive-inspect.json'), ('diagnose_project', 'openrive-diagnostics.json')]:
        result = client.call(tool, dict(project=project))
        (qa/name).write_text(json.dumps(result, indent=2))
        if tool == 'diagnose_project':
            assert result['valid'], result
            print(json.dumps(result), flush=True)
    result = client.call('export_riv', dict(project=project))
    data = base64.b64decode(result['dataBase64'])
    (ROOT/'luon.riv').write_bytes(data)
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'], indent=2))
    (qa/'manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), rive_sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), vertices=len(vertices), canvas=[WIDTH, HEIGHT], svg_offset=OFFSET, loop_seconds=FRAMES/60, default_is_swimming=False), indent=2))
    runtime = ROOT/'runtime'; runtime.mkdir(exist_ok=True)
    for name in ['canvas_advanced.mjs', 'rive.wasm', 'rive_fallback.wasm', 'package.json']:
        shutil.copyfile(REPO/'fish/runtime'/name, runtime/name)
    print(meta['editor_url'], flush=True)


if __name__ == '__main__':
    main()
