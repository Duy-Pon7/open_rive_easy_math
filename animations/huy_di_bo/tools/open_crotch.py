"""Update only the shorts outline and its morph tracks through OpenRive MCP."""
import base64
import copy
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from deformation import PROPERTY_KEYS
from openrive_client import OpenRive

ROOT = Path(__file__).resolve().parents[1]


def main():
    meta = json.loads((ROOT / 'openrive.json').read_text())
    client = OpenRive(meta['base_url'])
    project = meta['project_id']
    snapshot = client.snapshot(project)
    doc = copy.deepcopy(snapshot['doc'])
    art = doc['artboards'][0]
    objects = art['objects']
    old_shape = next(o for o in objects if o['props'].get('name') == 'ShortsContour')
    removed = {old_shape['id']}
    while True:
        children = {o['id'] for o in objects if o['props'].get('parentId') in removed}
        if children <= removed:
            break
        removed |= children

    source = ET.parse(ROOT / 'source/scene.rml').getroot().find('Artboard')
    shape = next(e for e in source.iter('Shape') if e.get('name') == 'ShortsContour')
    mapping = {}
    rebuilt = []

    def convert(element, parent):
        props = {'parentId': parent}
        for key, value in element.attrib.items():
            if key == 'id' or key == 'fillRule':
                continue
            if key == 'name':
                props[key] = value
            elif key == 'colorValue':
                props[key] = int(value, 16)
            elif value in ['true', 'false']:
                props[key] = value == 'true'
            else:
                props[key] = float(value)
        obj = {'id': 'crotch-' + uuid.uuid4().hex, 'type': element.tag, 'props': props}
        mapping[element.get('id')] = obj['id']
        rebuilt.append(obj)
        for child in element:
            convert(child, obj['id'])

    convert(shape, old_shape['props']['parentId'])
    index = objects.index(old_shape)
    art['objects'] = [o for o in objects[:index] if o['id'] not in removed] + rebuilt + [
        o for o in objects[index:] if o['id'] not in removed]
    source_animations = {e.get('name'): e for e in source.findall('LinearAnimation')}

    def item(kind, props, children=None):
        obj = {'id': 'crotch-' + uuid.uuid4().hex, 'type': kind, 'props': props}
        if children is not None:
            obj['children'] = children
        return obj

    for animation in art['animations']:
        animation['children'] = [o for o in animation.get('children', [])
                                 if o['props'].get('objectId') not in removed]
        for keyed in source_animations[animation['props']['name']]:
            target = mapping.get(keyed.get('objectId'))
            if target is None:
                continue
            properties = []
            for prop in keyed:
                keys = [item('KeyFrameDouble', {'frame': float(k.get('frame')),
                        'value': float(k.get('value')), 'interpolationType': 1}) for k in prop]
                properties.append(item('KeyedProperty', {'propertyKey': PROPERTY_KEYS[prop.get('property')]}, keys))
            animation['children'].append(item('KeyedObject', {'objectId': target}, properties))

    # Everything outside the outline and its animation targets must be identical.
    assert [o for o in art['objects'] if o['id'] not in {o['id'] for o in rebuilt}] == [
        o for o in objects if o['id'] not in removed]
    assert art['stateMachines'] == snapshot['doc']['artboards'][0]['stateMachines']
    client.update(project, doc, snapshot['meta']['updatedAt'])
    diagnostics = client.call('diagnose_project', {'project': project})
    assert diagnostics['valid'], diagnostics
    exported = client.call('export_riv', {'project': project})
    (ROOT / 'huy_di_bo.riv').write_bytes(base64.b64decode(exported['dataBase64']))
    (ROOT / 'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'], indent=2))
    (ROOT / 'verification/openrive-diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    (ROOT / 'verification/crotch-update.json').write_text(json.dumps({
        'project_id': project, 'valid': diagnostics['valid'], 'removed_objects': len(removed),
        'new_objects': len(rebuilt), 'other_objects_unchanged': True,
        'state_machine_unchanged': True}, indent=2))
    print(json.dumps(diagnostics), flush=True)


if __name__ == '__main__':
    main()
