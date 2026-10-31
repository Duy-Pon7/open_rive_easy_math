"""Add idle_left/walk_left to the current OpenRive file, retaining blink layers."""
import base64
import copy
import json
from pathlib import Path
import uuid
import requests
from directions import STATES

ROOT=Path(__file__).resolve().parents[1]


def uid():return 'direction-'+uuid.uuid4().hex


def node(kind,props=None,children=None):
    value={'id':uid(),'type':kind,'props':props or {}}
    if children is not None:value['children']=children
    return value


def main():
    meta=json.loads((ROOT/'openrive.json').read_text());base=meta['base_url'];project=meta['project_id']
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream';url=base+'/api/mcp'
    r=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'co-left-states','version':'1'}}},timeout=30)
    r.raise_for_status();session.headers['mcp-session-id']=r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def call(name,arguments):
        r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=180)
        r.raise_for_status();payload=r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
        result=payload['result'];structured=result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])
    def snapshot():
        r=session.get(base+'/api/projects/'+project,timeout=90);r.raise_for_status();return r.json()
    before=snapshot();qa=ROOT/'verification';backup=qa/'before-left-states-project.json'
    if not backup.exists():
        backup.write_text(json.dumps(before,indent=2));(qa/'before-left-states.riv').write_bytes((ROOT/'co_di_bo.riv').read_bytes())
    if not any(o['props'].get('name')=='FacingRoot' for o in before['doc']['artboards'][0]['objects']):
        result=call('add_group',{'project':project,'name':'FacingRoot','x':0,'y':0})
        (qa/'direction-mcp.json').write_text(json.dumps(result,indent=2))
    snap=snapshot();doc=snap['doc'];art=doc['artboards'][0];objects=art['objects']
    wrapper=next(o for o in objects if o['props'].get('name')=='FacingRoot')
    root=next(o for o in objects if o['props'].get('name')=='CharacterRoot')
    root['props']['parentId']=wrapper['id']
    wrapper['props'].update(x=0,y=0,scaleX=1,scaleY=1)
    def direction_keys(animation,left):
        animation['children']=[c for c in animation.get('children',[]) if c['props'].get('objectId')!=wrapper['id']]
        properties=[]
        for property_key,value in [(13,489 if left else 0),(16,-1 if left else 1)]:
            properties.append(node('KeyedProperty',{'propertyKey':property_key},[
                node('KeyFrameDouble',{'frame':f,'value':value,'interpolationType':1}) for f in [0,animation['props'].get('duration',60)]]))
        animation['children'].append(node('KeyedObject',{'objectId':wrapper['id']},properties))
    animations={a['props']['name']:a for a in art['animations']}
    for source,target in [('idle','idle_left'),('walk','walk_left')]:
        if target not in animations:
            clone=copy.deepcopy(animations[source])
            def reidentify(n):
                n['id']=uid()
                for child in n.get('children',[]):reidentify(child)
            reidentify(clone);clone['props']['name']=target
            art['animations'].append(clone);animations[target]=clone
        direction_keys(animations[target],True);direction_keys(animations[source],False)
    sm=next(s for s in art['stateMachines'] if s['props'].get('name')=='CoWalkController')
    blink_before=copy.deepcopy(next(c for c in sm['children'] if c['props'].get('name')=='Blinking'))
    facing=next((c for c in sm['children'] if c['props'].get('name')=='facing_left'),None)
    if facing is None:
        facing=node('StateMachineBool',{'name':'facing_left','value':False});sm['children'].insert(2,facing)
    walking=next(c for c in sm['children'] if c['props'].get('name')=='is_walking')
    layer=next(c for c in sm['children'] if c['type']=='StateMachineLayer' and c['props'].get('name')=='Walking')
    states=[node('AnimationState',{'animationId':animations[name]['id'],'flags':2},[]) for name,_,_ in STATES]
    entry=node('EntryState',{},[])
    for source_index,source in [(-1,entry),*enumerate(states)]:
        for target_index,(name,is_walking,is_left) in enumerate(STATES):
            if source_index==target_index:continue
            same_face=source_index>=0 and STATES[source_index][2]==is_left
            source['children'].append(node('StateTransition',{'stateToId':states[target_index]['id'],'flags':32,'duration':180 if same_face else 0},[
                node('TransitionBoolCondition',{'inputId':walking['id'],'opValue':0 if is_walking else 1}),
                node('TransitionBoolCondition',{'inputId':facing['id'],'opValue':0 if is_left else 1})]))
    layer['children']=[node('AnyState'),node('ExitState'),entry]+states
    assert blink_before==next(c for c in sm['children'] if c['props'].get('name')=='Blinking')
    r=session.put(base+'/api/projects/'+project,json={'doc':json.dumps(doc),'expectedUpdatedAt':snap['meta']['updatedAt']},timeout=120)
    r.raise_for_status()
    diagnostic=call('diagnose_project',{'project':project})
    (qa/'openrive-diagnostics.json').write_text(json.dumps(diagnostic,indent=2));assert diagnostic['valid'],diagnostic
    result=call('export_riv',{'project':project});(ROOT/'co_di_bo.riv').write_bytes(base64.b64decode(result['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(snapshot()['doc'],indent=2))
    result=call('get_project',{'project':project});(qa/'openrive-inspect.json').write_text(json.dumps(result,indent=2))
    print('Diagnostics:',json.dumps(diagnostic),flush=True);print(meta['editor_url'],flush=True)


if __name__=='__main__':main()
