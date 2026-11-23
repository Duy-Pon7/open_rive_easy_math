"""Sync the independent skirt, jacket and rigid leg silhouettes through OpenRive MCP."""
import base64
import copy
import json
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET
from deformation import PROPERTY_KEYS

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'huy_di_bo/tools'))
from openrive_client import OpenRive


def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    client=OpenRive(meta['base_url']);project=meta['project_id']
    snapshot=client.snapshot(project);doc=copy.deepcopy(snapshot['doc'])
    art=doc['artboards'][0];objects=art['objects']
    targets={f'SVG_{i:03d}' for i in [*range(9),12,*range(36,53)]}
    source=ET.parse(ROOT/'source/scene.rml').getroot().find('Artboard')
    sources={e.get('name'):e for e in source.iter('Shape')}
    removed={o['id'] for o in objects if o['props'].get('name') in targets}
    while True:
        children={o['id'] for o in objects if o['props'].get('parentId') in removed}
        if children<=removed:break
        removed|=children
    mapping={};rebuilt=[]
    def convert(element,parent):
        props={'parentId':parent}
        for key,value in element.attrib.items():
            if key in ['id','fillRule']:continue
            if key=='name':props[key]=value
            elif key=='colorValue':props[key]=int(value,16)
            elif value in ['true','false']:props[key]=value=='true'
            else:props[key]=float(value)
        obj={'id':'arm-fix-'+uuid.uuid4().hex,'type':element.tag,'props':props}
        mapping[element.get('id')]=obj['id'];rebuilt.append(obj)
        for child in element:convert(child,obj['id'])
    updated=[]
    for obj in objects:
        name=obj['props'].get('name')
        if obj['type']=='Shape' and name in targets:
            start=len(rebuilt);convert(sources[name],obj['props']['parentId'])
            updated.extend(rebuilt[start:])
        elif obj['id'] not in removed:updated.append(obj)
    # Rive draws siblings front to back. The jacket must cover the newly
    # concealed skirt waistband, while the hands remain in front of both.
    jacket=next(o for o in updated if o['props'].get('name')=='SVG_000')
    jacket_ids={jacket['id']}
    while True:
        descendants={o['id'] for o in updated if o['props'].get('parentId') in jacket_ids}
        if descendants<=jacket_ids:break
        jacket_ids|=descendants
    jacket_block=[o for o in updated if o['id'] in jacket_ids]
    updated=[o for o in updated if o['id'] not in jacket_ids]
    index=next(i for i,o in enumerate(updated) if o['props'].get('name')=='SVG_001')
    updated[index:index]=jacket_block
    art['objects']=updated
    def item(kind,props,children=None):
        obj={'id':'arm-fix-'+uuid.uuid4().hex,'type':kind,'props':props}
        if children is not None:obj['children']=children
        return obj
    joint_names={o['props'].get('name'):o for o in objects if o['props'].get('name','').endswith('Joint')}
    joint_ids={o['id'] for o in joint_names.values()}
    for element in source.iter('Node'):
        if element.get('name') in joint_names:mapping[element.get('id')]=joint_names[element.get('name')]['id']
    keyed_targets=removed|joint_ids
    animations={a.get('name'):a for a in source.findall('LinearAnimation')}
    for animation in art['animations']:
        animation['children']=[o for o in animation.get('children',[]) if o['props'].get('objectId') not in keyed_targets]
        for keyed in animations[animation['props']['name']]:
            target=mapping.get(keyed.get('objectId'))
            if target is None:continue
            props=[]
            for prop in keyed:
                keys=[item('KeyFrameDouble',{'frame':float(k.get('frame')),'value':float(k.get('value')),'interpolationType':1}) for k in prop]
                props.append(item('KeyedProperty',{'propertyKey':({'x':13,'y':14}[prop.get('property')] if target in joint_ids else PROPERTY_KEYS[prop.get('property')])},keys))
            animation['children'].append(item('KeyedObject',{'objectId':target},props))
    new_ids={o['id'] for o in rebuilt}
    new_keyed_ids=new_ids|joint_ids
    assert [o for o in art['objects'] if o['id'] not in new_ids]==[o for o in objects if o['id'] not in removed]
    before=snapshot['doc']['artboards'][0]
    assert art['stateMachines']==before['stateMachines']
    for new,old in zip(art['animations'],before['animations']):
        assert [o for o in new['children'] if o['props'].get('objectId') not in new_keyed_ids]==[
            o for o in old['children'] if o['props'].get('objectId') not in keyed_targets]
    client.update(project,doc,snapshot['meta']['updatedAt'])
    diagnostics=client.call('diagnose_project',{'project':project});assert diagnostics['valid'],diagnostics
    data=client.call('export_riv',{'project':project})
    (ROOT/'vy_di_bo.riv').write_bytes(base64.b64decode(data['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'],indent=2))
    (ROOT/'verification/openrive-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    (ROOT/'verification/legs-skirt-update.json').write_text(json.dumps({
        'project_id':project,'valid':diagnostics['valid'],'other_objects_unchanged':True,
        'other_animation_tracks_unchanged':True,'state_machine_unchanged':True,
        'removed_objects':len(removed),'new_objects':len(rebuilt)},indent=2))
    print(json.dumps(diagnostics),flush=True)


if __name__=='__main__':main()
