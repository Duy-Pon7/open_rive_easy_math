"""Create the native-vector speaker and its two states over local OpenRive MCP."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import math
import xml.etree.ElementTree as ET

from svgpathtools import parse_path, CubicBezier, Line

ROOT = Path(__file__).resolve().parents[1]
from mcp_client import OpenRive


def points(data, anchor):
    contours = parse_path(data).continuous_subpaths()
    assert len(contours) == 1 and contours[0].isclosed()
    segs = list(contours[0])
    result = []
    for i, seg in enumerate(segs):
        prev = segs[i - 1]
        assert isinstance(seg, (CubicBezier, Line))
        start = seg.start
        incoming = prev.control2 - start if isinstance(prev, CubicBezier) else 0j
        outgoing = seg.control1 - start if isinstance(seg, CubicBezier) else 0j
        result.append(dict(x=start.real-anchor[0], y=start.imag-anchor[1],
                           inX=incoming.real, inY=incoming.imag,
                           outX=outgoing.real, outY=outgoing.imag))
    return result


def key(obj, prop, samples, timeline='playing'):
    return dict(op='add_keyframes', timeline=timeline, object=obj, property=prop,
                keys=[dict(frame=f, value=v, ease='linear') for f, v in samples])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:56545')
    args = parser.parse_args()
    qa = ROOT / 'verification'
    qa.mkdir(exist_ok=True)
    client = OpenRive(args.base)
    meta_path = ROOT / 'openrive.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        project = meta['project_id']
    else:
        created = client.call('create_project', {'name': 'Loa Doc - Audio Playback'})
        print('created', json.dumps(created), flush=True)
        project = created.get('id') or created.get('projectId') or created.get('project', {}).get('id')
        if not project:
            raise RuntimeError(created)
        meta = dict(project_id=project, phase='created')
    meta.update(base_url=args.base, editor_url=args.base + '/editor/' + project)
    meta_path.write_text(json.dumps(meta, indent=2))

    def call(tool_name, **kwargs):
        return client.call(tool_name, dict(project=project, **kwargs))

    if meta.get('phase') == 'created':
        # The blank template already contains a first artboard.
        initial = call('get_project')['artboards'][0]
        call('set_properties', object=initial['id'], properties=dict(name='Loa Doc', width=1254, height=1254))
        meta['phase'] = 'artboard'
        meta_path.write_text(json.dumps(meta, indent=2))
    if meta.get('phase') == 'artboard':
        svg = list(ET.parse(ROOT / 'loa_doc.svg').getroot())
        ops = [dict(op='add_group', name='Speaker', x=430, y=720)]
        ray_index = 0
        for i, element in enumerate(svg):
            is_ray = element.get('fill') == '#FEDF3F'
            if is_ray:
                ray_index += 1
                name = 'Sound Ray ' + str(ray_index)
                anchor = (820, 615)
                parent = None
            else:
                name = 'Speaker Vector ' + str(i+1)
                anchor = (430, 720)
                parent = 'Speaker'
            op = dict(op='add_path', name=name, x=anchor[0] if is_ray else 0,
                      y=anchor[1] if is_ray else 0, points=points(element.get('d'), anchor),
                      closed=True, fill=element.get('fill'))
            if parent:
                op['parent'] = parent
            ops.append(op)
        call('apply_edit_plan', operations=ops)
        meta.update(phase='vectors', ray_count=ray_index)
        meta_path.write_text(json.dumps(meta, indent=2))

    if meta.get('phase') == 'vectors':
        ops = [dict(op='add_timeline', name='idle', duration=1, fps=60, loop='loop'),
               dict(op='add_timeline', name='playing', duration=1.2, fps=60, loop='loop')]
        for prop, value in [('rotationDegrees', 0), ('scaleX', 1), ('scaleY', 1)]:
            ops.append(key('Speaker', prop, [(0, value), (60, value)], 'idle'))
        # Low-amplitude vibration keeps every original detail legible.
        frames = list(range(0, 73, 3))
        ops.append(key('Speaker', 'rotationDegrees', [(f, round(.7*math.sin(2*math.pi*f/18), 6)) for f in frames]))
        ops.append(key('Speaker', 'scaleX', [(f, round(1+.009*math.sin(2*math.pi*f/24), 6)) for f in frames]))
        ops.append(key('Speaker', 'scaleY', [(f, round(1+.006*math.sin(2*math.pi*f/24), 6)) for f in frames]))
        for i in range(1, meta['ray_count']+1):
            name = 'Sound Ray ' + str(i)
            for prop, value in [('opacity', 0), ('scaleX', 1), ('scaleY', 1)]:
                ops.append(key(name, prop, [(0, value), (60, value)], 'idle'))
            # The middle ray leads; the two outer pairs follow in a repeating wave.
            phase = {1:0, 2:4, 3:4, 4:8, 5:8}[i]
            samples = []
            scales = []
            for f in frames:
                pulse = (.5+.5*math.cos(2*math.pi*(f-phase)/36))**1.6
                samples.append((f, round(.18+.82*pulse, 6)))
                scales.append((f, round(.965+.035*pulse, 6)))
            ops.append(key(name, 'opacity', samples))
            ops.append(key(name, 'scaleX', scales))
            ops.append(key(name, 'scaleY', scales))
        ops.extend([
            dict(op='add_state_machine', name='LoaDocController'),
            dict(op='add_property', type='boolean', name='is_playing', value=False),
            dict(op='add_state', stateMachine='LoaDocController', timeline='idle'),
            dict(op='add_state', stateMachine='LoaDocController', timeline='playing'),
            dict(op='add_transition', stateMachine='LoaDocController', **{'from':'entry', 'to':'idle'}, durationMs=0),
            dict(op='add_transition', stateMachine='LoaDocController', **{'from':'idle', 'to':'playing'}, durationMs=120,
                 conditions=[dict(property='is_playing', value=True)]),
            dict(op='add_transition', stateMachine='LoaDocController', **{'from':'playing', 'to':'idle'}, durationMs=160,
                 conditions=[dict(property='is_playing', value=False)]),
        ])
        (qa/'edit_plan.json').write_text(json.dumps(ops, indent=2))
        result = call('apply_edit_plan', operations=ops)
        (qa/'animation-mcp.json').write_text(json.dumps(result, indent=2))
        meta['phase'] = 'animated'
        meta_path.write_text(json.dumps(meta, indent=2))

    # The blank template carries a starter artboard/timeline/controller. Tools
    # default to that first artboard, so retain the authored one and clean the
    # untouched starter scaffolding before exporting.
    snapshot = client.snapshot(project)
    doc = snapshot['doc']
    if isinstance(doc, str):
        doc = json.loads(doc)
    art = next(a for a in doc['artboards'] if any(
        m['props'].get('name') == 'LoaDocController' for m in a['stateMachines']))
    art['artboard']['props'].update(name='Loa Doc', width=1254, height=1254)
    art['animations'] = [a for a in art['animations'] if a['props'].get('name') in ['idle', 'playing']]
    art['stateMachines'] = [s for s in art['stateMachines'] if s['props'].get('name') == 'LoaDocController']
    art['artboard']['props']['defaultStateMachineId'] = art['stateMachines'][0]['id']
    background_ids = {o['id'] for o in art['objects']
                      if o['type'] == 'Fill' and o['props'].get('parentId') == art['id']}
    art['objects'] = [o for o in art['objects'] if o['id'] not in background_ids
                      and o['props'].get('parentId') not in background_ids]
    for obj in art['objects']:
        if obj['type'] == 'Shape' and obj['props'].get('name', '').startswith('Sound Ray '):
            obj['props']['opacity'] = 0
    doc['artboards'] = [art]
    client.update(project, doc, snapshot['meta']['updatedAt'])

    for name, filename in [('get_project','openrive-inspect.json'), ('diagnose_project','openrive-diagnostics.json')]:
        result = call(name)
        (qa/filename).write_text(json.dumps(result, indent=2))
        if name == 'diagnose_project':
            print('diagnostics', json.dumps(result), flush=True)
    exported = call('export_riv')
    data = base64.b64decode(exported['dataBase64'])
    (ROOT/'loa_doc.riv').write_bytes(data)
    snapshot = client.snapshot(project)
    (ROOT/'openrive-project.json').write_text(json.dumps(snapshot['doc'], indent=2))
    (qa/'source_manifest.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256((ROOT/'loa_doc.svg').read_bytes()).hexdigest(),
        riv_sha256=hashlib.sha256(data).hexdigest(), native_vectors=True,
        canvas=[1254,1254], timelines=['idle','playing'], state_machine='LoaDocController',
        boolean_property='is_playing', default=False, loop_seconds=1.2), indent=2))
    print(meta['editor_url'], 'exported', len(data), 'bytes', flush=True)


if __name__ == '__main__':
    main()
