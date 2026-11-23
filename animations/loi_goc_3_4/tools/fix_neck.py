"""Repair the existing Loi project and its source, preserving animation ids."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import xml.etree.ElementTree as ET

import requests
import build_loi
from neck_geometry import NECK_PATH, BACKING_PATH, COLLAR_UNDERLAP_PATH

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT/'verification'
ASSET = ROOT/'loi_goc_3_4_noi_speaking_vi.riv'


def uid():
    return secrets.token_urlsafe(8)


def vertices(path_id, data):
    shape = ET.Element('Shape')
    build_loi.path_geometry(shape, data)
    assert len(shape) == 1
    return [dict(id=uid(), type=v.tag,
                 props={**{k: float(val) for k, val in v.attrib.items() if k != 'id'},
                        'parentId': path_id}) for v in shape[0]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:50829')
    args = parser.parse_args()
    metadata = json.loads((ROOT/'openrive.json').read_text(encoding='utf8'))
    project = metadata['project_id']
    session = requests.Session()
    session.headers['Accept'] = 'application/json, text/event-stream'
    url = args.base + '/api/mcp'
    sequence = 0

    def rpc(method, params):
        nonlocal sequence
        sequence += 1
        response = session.post(url, json=dict(jsonrpc='2.0', id=sequence,
                                method=method, params=params), timeout=90)
        response.raise_for_status()
        if response.headers.get('mcp-session-id'):
            session.headers['mcp-session-id'] = response.headers['mcp-session-id']
        payload = response.json()
        if 'error' in payload:
            raise RuntimeError(payload)
        return payload['result']

    def call(name, **arguments):
        result = rpc('tools/call', dict(name=name, arguments=arguments))
        if result.get('isError'):
            raise RuntimeError(result)
        return result.get('structuredContent', {}).get('result') or json.loads(result['content'][0]['text'])

    rpc('initialize', dict(protocolVersion='2024-11-05', capabilities={},
                          clientInfo=dict(name='loi-neck-repair', version='1')))
    session.post(url, json=dict(jsonrpc='2.0', method='notifications/initialized'), timeout=20).raise_for_status()
    response = session.get(args.base+'/api/projects/'+project, timeout=30)
    response.raise_for_status()
    snapshot = response.json()
    document = copy.deepcopy(snapshot['doc'])
    artboard = document['artboards'][0]
    objects = artboard['objects']
    if any(o.get('props', {}).get('name') == 'FixedNeck' for o in objects):
        raise RuntimeError('Neck already repaired; refusing to apply twice.')
    before = base64.b64decode(call('export_riv', project=project)['dataBase64'])
    if before != ASSET.read_bytes():
        raise RuntimeError('The live project and requested .riv differ; no edits applied.')
    backup = QA/'before_neck_fix'
    backup.mkdir(exist_ok=False)
    for path in (ASSET, ROOT/'openrive-project.json', ROOT/'openrive.json', ROOT/'source/scene.rml'):
        shutil.copy2(path, backup/path.name)
    (backup/'live-snapshot.json').write_text(json.dumps(snapshot, indent=2), encoding='utf8')

    def named(name):
        return next(o for o in objects if o.get('props', {}).get('name') == name)

    def replace_path(shape, data):
        path = next(o for o in objects if o.get('props', {}).get('parentId') == shape['id'] and o['type'] == 'PointsPath')
        old = [o for o in objects if o.get('props', {}).get('parentId') == path['id']]
        keyed = {ko['props'].get('objectId') for anim in artboard['animations'] for ko in anim.get('children', [])}
        assert not keyed.intersection(o['id'] for o in old)
        at = objects.index(old[0])
        objects[:] = [o for o in objects if o not in old]
        objects[at:at] = vertices(path['id'], data)

    replace_path(named('SVG_040'), NECK_PATH)
    replace_path(named('NeckBacking'), BACKING_PATH)
    group = dict(id=uid(), type='Node', props=dict(name='FixedNeck', parentId=named('CharacterRoot')['id']))
    moved = {named('SVG_040')['id'], named('SVG_041')['id']}
    for o in objects:
        if o.get('props', {}).get('parentId') in moved:
            moved.add(o['id'])
    block = [o for o in objects if o['id'] in moved]
    for name in ('SVG_040', 'SVG_041'):
        named(name)['props']['parentId'] = group['id']
    objects[:] = [o for o in objects if o['id'] not in moved]
    at = objects.index(named('Body'))
    objects[at:at] = [group, *block]
    collar = dict(id=uid(), type='Shape', props=dict(name='CollarUnderlap', parentId=named('Body')['id']))
    path = dict(id=uid(), type='PointsPath', props=dict(isClosed=True, parentId=collar['id']))
    fill = dict(id=uid(), type='Fill', props=dict(parentId=collar['id']))
    paint = dict(id=uid(), type='SolidColor', props=dict(parentId=fill['id'], colorValue=0xFF1A1919))
    at = objects.index(named('NeckBacking'))
    objects[at:at] = [collar, path, *vertices(path['id'], COLLAR_UNDERLAP_PATH), fill, paint]
    response = session.put(args.base+'/api/projects/'+project,
                           json=dict(doc=json.dumps(document), expectedUpdatedAt=snapshot['meta']['updatedAt']), timeout=60)
    response.raise_for_status()
    diagnostics = call('diagnose_project', project=project)
    (QA/'neck-diagnostics.json').write_text(json.dumps(diagnostics, indent=2), encoding='utf8')
    assert diagnostics['valid'] and not diagnostics['diagnostics'], diagnostics
    output = base64.b64decode(call('export_riv', project=project)['dataBase64'])
    ASSET.write_bytes(output)
    (ROOT/'openrive-project.json').write_text(json.dumps(document, indent=2), encoding='utf8')
    metadata.update(base_url=args.base, editor_url=args.base+'/editor/'+project)
    (ROOT/'openrive.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')

    tree = ET.parse(ROOT/'source/scene.rml')
    root = tree.getroot()
    build_loi.counter = max(int(e.get('id').split(':')[-1]) for e in root.iter() if e.get('id'))
    def xml_named(name):
        return next(e for e in root.iter() if e.get('name') == name)
    for name, data in [('SVG_040', NECK_PATH), ('NeckBacking', BACKING_PATH)]:
        shape = xml_named(name)
        for child in list(shape):
            if child.tag == 'PointsPath':
                shape.remove(child)
        build_loi.path_geometry(shape, data)
    rig = xml_named('CharacterRoot')
    group_xml = build_loi.add(rig, 'Node', name='FixedNeck')
    rig.remove(group_xml)
    rig.insert(list(rig).index(xml_named('Body')), group_xml)
    for name in ('SVG_041', 'SVG_040'):
        shape = xml_named(name)
        for parent in root.iter():
            if shape in list(parent):
                parent.remove(shape)
                break
        group_xml.append(shape)
    collar_xml = build_loi.add(xml_named('Body'), 'Shape', name='CollarUnderlap')
    build_loi.path_geometry(collar_xml, COLLAR_UNDERLAP_PATH)
    build_loi.color(build_loi.add(collar_xml, 'Fill'), '#1A1919')
    ET.indent(tree, space='  ')
    tree.write(ROOT/'source/scene.rml', encoding='utf-8', xml_declaration=True)
    report = dict(project=project, before_bytes=len(before), after_bytes=len(output),
                  sha256=hashlib.sha256(output).hexdigest(),
                  changes=['Anchor neck and shadow to shirt', 'Smooth neck sides',
                           'Inset backing', 'Overlap shirt beneath neckline'])
    (QA/'neck-repair.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
