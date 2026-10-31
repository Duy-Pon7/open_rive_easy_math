"""Sync the separated black garment and arm/sash tracks to OpenRive MCP."""
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
    targets={f'SVG_{i:03d}' for i in [0,1,2,3,4,5,6,34,35,36,37,39,53,54,55,85]}
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
            if name=='SVG_000':convert(sources['TrousersContour'],obj['props']['parentId'])
            updated.extend(rebuilt[start:])
        elif obj['id'] not in removed:updated.append(obj)
    art['objects']=updated
    def item(kind,props,children=None):
        obj={'id':'arm-fix-'+uuid.uuid4().hex,'type':kind,'props':props}
        if children is not None:obj['children']=children
        return obj
    animations={a.get('name'):a for a in source.findall('LinearAnimation')}
    for animation in art['animations']:
        animation['children']=[o for o in animation.get('children',[]) if o['props'].get('objectId') not in removed]
        for keyed in animations[animation['props']['name']]:
            target=mapping.get(keyed.get('objectId'))
            if target is None:continue
            props=[]
            for prop in keyed:
                keys=[item('KeyFrameDouble',{'frame':float(k.get('frame')),'value':float(k.get('value')),'interpolationType':1}) for k in prop]
                props.append(item('KeyedProperty',{'propertyKey':PROPERTY_KEYS[prop.get('property')]},keys))
            animation['children'].append(item('KeyedObject',{'objectId':target},props))
    new_ids={o['id'] for o in rebuilt}
    assert [o for o in art['objects'] if o['id'] not in new_ids]==[o for o in objects if o['id'] not in removed]
    before=snapshot['doc']['artboards'][0]
    assert art['stateMachines']==before['stateMachines']
    for new,old in zip(art['animations'],before['animations']):
        assert [o for o in new['children'] if o['props'].get('objectId') not in new_ids]==[
            o for o in old['children'] if o['props'].get('objectId') not in removed]
    client.update(project,doc,snapshot['meta']['updatedAt'])
    diagnostics=client.call('diagnose_project',{'project':project});assert diagnostics['valid'],diagnostics
    data=client.call('export_riv',{'project':project})
    (ROOT/'loi_di_bo.riv').write_bytes(base64.b64decode(data['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'],indent=2))
    (ROOT/'verification/openrive-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    (ROOT/'verification/arm-underlay-update.json').write_text(json.dumps({
        'project_id':project,'valid':diagnostics['valid'],'other_objects_unchanged':True,
        'other_animation_tracks_unchanged':True,'state_machine_unchanged':True,
        'removed_objects':len(removed),'new_objects':len(rebuilt)},indent=2))
    print(json.dumps(diagnostics),flush=True)


if __name__=='__main__':main()
