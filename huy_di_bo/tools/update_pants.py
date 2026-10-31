"""Replace the garment rig in the existing project, preserving its face/controller."""
import base64
import copy
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
from motion import node_tracks
from deformation import PROPERTY_KEYS
from openrive_client import OpenRive

ROOT=Path(__file__).resolve().parents[1]
PROPERTY_KEYS={**PROPERTY_KEYS,'x':13,'y':14,'rotation':15,'scaleX':16,'scaleY':17,'opacity':18}

def item(kind,props=None,children=None):
    result={'id':'pants-'+uuid.uuid4().hex,'type':kind,'props':props or {}}
    if children is not None:result['children']=children
    return result

def main():
    qa=ROOT/'verification';meta=json.loads((ROOT/'openrive.json').read_text())
    client=OpenRive(meta['base_url']);project=meta['project_id'];snapshot=client.snapshot(project)
    if not (qa/'before-pants-snapshot.json').exists():
        (qa/'before-pants-snapshot.json').write_text(json.dumps(snapshot,indent=2))
        data=client.call('export_riv',{'project':project})
        (qa/'before-pants.riv').write_bytes(base64.b64decode(data['dataBase64']))
    doc=copy.deepcopy(snapshot['doc']);art=doc['artboards'][0];objects=art['objects']
    names={o['props'].get('name'):o for o in objects}
    preserved_sm=copy.deepcopy(art['stateMachines'])
    preserved_blinks=[copy.deepcopy(a) for a in art['animations'] if a['props']['name'].startswith('blink_')]
    source=ET.parse(ROOT/'source/scene.rml').getroot().find('Artboard')
    source_names={e.get('name'):e for e in source.iter() if e.get('name')}
    removed={names[n]['id'] for n in ['Garment','Trousers'] if n in names}
    while True:
        descendants={o['id'] for o in objects if o['props'].get('parentId') in removed}
        if descendants<=removed:break
        removed|=descendants
    insertion=min(i for i,o in enumerate(objects) if o['id'] in removed)
    mapping={source_names[n].get('id'):o['id'] for n,o in names.items() if n in source_names and o['id'] not in removed}
    rebuilt=[]
    def convert(element,parent):
        props={}
        for name,value in element.attrib.items():
            if name=='id':continue
            if name=='name':props[name]=value
            elif name=='colorValue':props[name]=int(value,16)
            elif name=='fillRule':
                assert value=='nonZero'
            elif value in ['true','false']:props[name]=value=='true'
            else:props[name]=float(value)
        props['parentId']=parent
        obj=item(element.tag,props);mapping[element.get('id')]=obj['id'];rebuilt.append(obj)
        for child in element:convert(child,obj['id'])
    parent=names['SVGCoordinates']['id']
    for name in ['Garment','Trousers']:convert(source_names[name],parent)
    art['objects']=[o for o in objects[:insertion] if o['id'] not in removed]+rebuilt+[
        o for o in objects[insertion:] if o['id'] not in removed]
    changed_nodes={names[n]['id'] for n,_ in node_tracks()[0]}
    rebuilt_ids={o['id'] for o in rebuilt};new_target_ids=rebuilt_ids|changed_nodes
    source_animations={a.get('name'):a for a in source if a.tag=='LinearAnimation'}
    for animation in art['animations']:
        name=animation['props']['name']
        if name not in ['idle','walk','idle_left','walk_left']:continue
        animation['children']=[o for o in animation.get('children',[]) if o['props'].get('objectId') not in removed|changed_nodes]
        for keyed in source_animations[name]:
            target=mapping.get(keyed.get('objectId'))
            if target not in new_target_ids:continue
            properties=[]
            for prop in keyed:
                # x/y on vertices have different property IDs from Node x/y.
                vertex=next((o for o in rebuilt if o['id']==target),{}).get('type')=='CubicDetachedVertex'
                key={'x':24,'y':25}.get(prop.get('property')) if vertex and prop.get('property') in ['x','y'] else PROPERTY_KEYS[prop.get('property')]
                properties.append(item('KeyedProperty',{'propertyKey':key},[
                    item('KeyFrameDouble',{'frame':float(k.get('frame')),'value':float(k.get('value')),'interpolationType':1}) for k in prop]))
            animation['children'].append(item('KeyedObject',{'objectId':target},properties))
    assert art['stateMachines']==preserved_sm
    assert [a for a in art['animations'] if a['props']['name'].startswith('blink_')]==preserved_blinks
    (qa/'pants-candidate-project.json').write_text(json.dumps(doc,indent=2))
    client.update(project,doc,snapshot['meta']['updatedAt'])
    diagnostics=client.call('diagnose_project',{'project':project});assert diagnostics['valid'],diagnostics
    (qa/'openrive-diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    exported=client.call('export_riv',{'project':project})
    (ROOT/'huy_di_bo.riv').write_bytes(base64.b64decode(exported['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(client.snapshot(project)['doc'],indent=2))
    (qa/'openrive-inspect.json').write_text(json.dumps(client.call('get_project',{'project':project}),indent=2))
    report={'project_id':project,'valid':diagnostics['valid'],'state_machine_unchanged':True,
            'blink_animations_unchanged':True,'rebuilt_static_objects':len(rebuilt),'removed_static_objects':len(removed)}
    (qa/'pants-update.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
