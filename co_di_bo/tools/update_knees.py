"""Update both walking directions with articulated knee motion in OpenRive."""
import base64
import copy
import json
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import requests
from build_walk import vec
from deformation import PROPS,PROPERTY_KEYS,refine_pants,vertex_tracks
from motion import FRAMES,LEG_BIND,node_tracks,pants

ROOT=Path(__file__).resolve().parents[1]


def item(kind,props=None,children=None):
    result={'id':'knee-'+uuid.uuid4().hex,'type':kind,'props':props or {}}
    if children is not None:result['children']=children
    return result


def keyed(obj,tracks):
    return item('KeyedObject',{'objectId':obj},[
        item('KeyedProperty',{'propertyKey':key},[
            item('KeyFrameDouble',{'frame':int(f),'value':float(v),'interpolationType':1}) for f,v in values])
        for key,values in tracks.items()])


def main():
    meta=json.loads((ROOT/'openrive.json').read_text());base=meta['base_url'];project=meta['project_id']
    s=requests.Session();s.headers['Accept']='application/json, text/event-stream';url=base+'/api/mcp'
    r=s.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'co-knee-articulation','version':'1'}}},timeout=30)
    r.raise_for_status();s.headers['mcp-session-id']=r.headers['mcp-session-id']
    s.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def call(name,args):
        r=s.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':args}},timeout=180)
        r.raise_for_status();p=r.json()
        if 'error' in p or p.get('result',{}).get('isError'):raise RuntimeError(p)
        res=p['result'];st=res.get('structuredContent',{})
        return st['result'] if 'result' in st else json.loads(res['content'][0]['text'])
    def snapshot():
        r=s.get(base+'/api/projects/'+project,timeout=90);r.raise_for_status();return r.json()
    snap=snapshot();qa=ROOT/'verification'
    if not (qa/'before-knees-project.json').exists():
        (qa/'before-knees-project.json').write_text(json.dumps(snap,indent=2))
        (qa/'before-knees.riv').write_bytes((ROOT/'co_di_bo.riv').read_bytes())
    names={o['props'].get('name') for o in snap['doc']['artboards'][0]['objects']}
    base_values,node_values=node_tracks();ops=[]
    if 'LegJoints' not in names:ops.append({'op':'add_group','parent':'SVGCoordinates','name':'LegJoints'})
    for (name,prop),value in base_values.items():
        if name.endswith('Joint') and prop=='x' and name not in names:
            ops.append({'op':'add_group','parent':'LegJoints','name':name,'x':value,'y':base_values[name,'y']})
    if ops:
        result=call('apply_edit_plan',{'project':project,'operations':ops})
        (qa/'knee-rig-mcp.json').write_text(json.dumps(result,indent=2))
    snap=snapshot();doc=snap['doc'];art=doc['artboards'][0];objects=art['objects']
    names={o['props'].get('name'):o for o in objects}
    shape=names['SVG_190'];path=next(o for o in objects if o['type']=='PointsPath' and o['props'].get('parentId')==shape['id'])
    old_vertices={o['id'] for o in objects if o['props'].get('parentId')==path['id']}
    temporary=ET.Element('Shape')
    svg=ET.parse(ROOT/'co_di_bo.svg').getroot()
    xml_vertices=vec.path_geometry(temporary,refine_pants(svg[190].get('d')))
    vertices=[item('CubicDetachedVertex',{**{p:float(v.get(p)) for p in PROPS},'parentId':path['id']}) for v in xml_vertices]
    index=min(i for i,o in enumerate(objects) if o['id'] in old_vertices)
    art['objects']=[o for o in objects[:index] if o['id'] not in old_vertices]+vertices+[o for o in objects[index:] if o['id'] not in old_vertices]
    morphs={v['id']:vertex_tracks(v['props'],pants) for v in vertices}
    changed_nodes={names[name]['id'] for name,_ in base_values}
    preserved={a['props']['name']:copy.deepcopy(a) for a in art['animations'] if a['props']['name'].startswith('blink_')}
    for animation in art['animations']:
        name=animation['props']['name']
        if name not in ['idle','walk','idle_left','walk_left']:continue
        walking=name.startswith('walk')
        animation['children']=[c for c in animation.get('children',[]) if c['props'].get('objectId') not in old_vertices|changed_nodes]
        for (node_name,prop),values in node_values.items():
            key={'x':13,'y':14,'rotationDegrees':15}[prop]
            values=[math.radians(v) for v in values] if prop=='rotationDegrees' else values
            rest=math.radians(base_values[node_name,prop]) if prop=='rotationDegrees' else base_values[node_name,prop]
            samples=list(enumerate(values)) if walking else [(0,rest),(60,rest)]
            animation['children'].append(keyed(names[node_name]['id'],{key:samples}))
        for vertex in vertices:
            props={PROPERTY_KEYS[prop]:keys if walking else [(0,vertex['props'][prop]),(60,vertex['props'][prop])]
                   for prop,keys in morphs[vertex['id']].items()}
            if props:animation['children'].append(keyed(vertex['id'],props))
    assert all(preserved[a['props']['name']]==a for a in art['animations'] if a['props']['name'].startswith('blink_'))
    r=s.put(base+'/api/projects/'+project,json={'doc':json.dumps(doc),'expectedUpdatedAt':snap['meta']['updatedAt']},timeout=120);r.raise_for_status()
    diagnostic=call('diagnose_project',{'project':project});assert diagnostic['valid'],diagnostic
    (qa/'openrive-diagnostics.json').write_text(json.dumps(diagnostic,indent=2))
    result=call('export_riv',{'project':project});(ROOT/'co_di_bo.riv').write_bytes(base64.b64decode(result['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(snapshot()['doc'],indent=2))
    result=call('get_project',{'project':project});(qa/'openrive-inspect.json').write_text(json.dumps(result,indent=2))
    print('Knee vertices:',len(vertices),flush=True)
    print('Diagnostics:',json.dumps(diagnostic),flush=True)


if __name__=='__main__':main()
