"""Add curved closed eyelids to the existing walking project through OpenRive."""
import base64
import json
from pathlib import Path
import uuid
import requests
from blinking import EYES,CURVES,AUTO_FRAMES,BLINK_FRAMES,animation_tracks

ROOT=Path(__file__).resolve().parents[1]


def main():
    meta=json.loads((ROOT/'openrive.json').read_text());base=meta['base_url'];project=meta['project_id']
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream'
    url=base+'/api/mcp'
    r=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'co-walk-eyelids','version':'1'}}},timeout=30)
    r.raise_for_status();session.headers['mcp-session-id']=r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def call(name,arguments):
        r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=180)
        r.raise_for_status();payload=r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
        result=payload['result'];structured=result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])
    def snapshot():
        r=session.get(base+'/api/projects/'+project,timeout=60);r.raise_for_status();return r.json()
    before=snapshot();qa=ROOT/'verification'
    backup=qa/'before-blink-project.json'
    if not backup.exists():
        backup.write_text(json.dumps(before,indent=2))
        (qa/'before-blink.riv').write_bytes((ROOT/'co_di_bo.riv').read_bytes())
    existing={o['props'].get('name') for o in before['doc']['artboards'][0]['objects']}
    ops=[]
    for name,x,y,_ in EYES:
        if name not in existing:
            ops += [{'op':'add_group','parent':'HeadCoordinates','name':name,'x':x,'y':y},
                    {'op':'add_group','parent':name,'name':name+'Coordinates','x':-x,'y':-y}]
    if 'ClosedEyes' not in existing:
        ops += [{'op':'add_group','parent':'HeadCoordinates','name':'ClosedEyes'},
                {'op':'set_properties','object':'ClosedEyes','properties':{'opacity':0}}]
    for name,points,color,width,opacity in CURVES:
        if name not in existing:
            a,b,c,d=points
            ops.append({'op':'add_path','name':name,'parent':'ClosedEyes','closed':False,
                'points':[{'x':a[0],'y':a[1],'outX':b[0]-a[0],'outY':b[1]-a[1]},
                          {'x':d[0],'y':d[1],'inX':c[0]-d[0],'inY':c[1]-d[1]}],
                'fill':'#00000000','stroke':color,'strokeWidth':width})
            ops.append({'op':'set_properties','object':name,'properties':{'opacity':opacity}})
    animations={a['props'].get('name') for a in before['doc']['artboards'][0]['animations']}
    for auto,name,frames in [(True,'blink_auto',AUTO_FRAMES),(False,'blink_once',BLINK_FRAMES)]:
        if name not in animations:ops.append({'op':'add_timeline','name':name,'fps':60,'duration':frames/60,'loop':'loop' if auto else 'oneShot'})
        for obj,prop,keys in animation_tracks(auto):
            ops.append({'op':'add_keyframes','timeline':name,'object':obj,'property':prop,
                        'keys':[{'frame':f,'value':v,'ease':'linear'} for f,v in keys]})
    result=call('apply_edit_plan',{'project':project,'operations':ops})
    (qa/'blink-mcp.json').write_text(json.dumps(result,indent=2))
    snap=snapshot();doc=snap['doc'];art=doc['artboards'][0];objects=art['objects']
    names={o['props'].get('name'):o for o in objects}
    for name,_,_,indices in EYES:
        for index in indices:names[f'SVG_{index:03d}']['props']['parentId']=names[name+'Coordinates']['id']
    for name,_,_,_,_ in CURVES:
        for stroke in objects:
            if stroke['type']=='Stroke' and stroke['props'].get('parentId')==names[name]['id']:
                stroke['props'].update(cap=1,join=1)
    # These nodes were inserted at the front by MCP, so the closed lashes
    # naturally cover the shrinking open eye during the brief crossfade.
    sm=next(s for s in art['stateMachines'] if s['props'].get('name')=='CoWalkController')
    def node(kind,props=None,children=None):
        out={'id':'blink-'+uuid.uuid4().hex,'type':kind,'props':props or {}}
        if children is not None:out['children']=children
        return out
    trigger=next((s for s in sm['children'] if s['props'].get('name')=='blink'),None)
    if trigger is None:
        trigger=node('StateMachineTrigger',{'name':'blink'});sm['children'].insert(1,trigger)
    if not any(c['type']=='StateMachineLayer' and c['props'].get('name')=='Blinking' for c in sm['children']):
        anims={a['props'].get('name'):a['id'] for a in art['animations']}
        automatic=node('AnimationState',{'animationId':anims['blink_auto'],'flags':2},[])
        manual=node('AnimationState',{'animationId':anims['blink_once'],'flags':2},[])
        automatic['children'].append(node('StateTransition',{'stateToId':manual['id']},[
            node('TransitionTriggerCondition',{'inputId':trigger['id']})]))
        manual['children'].append(node('StateTransition',{'stateToId':automatic['id'],'flags':12,'exitTime':100}))
        entry=node('EntryState',{},[node('StateTransition',{'stateToId':automatic['id']})])
        sm['children'].append(node('StateMachineLayer',{'name':'Blinking'},[node('AnyState'),node('ExitState'),entry,automatic,manual]))
    old_art=before['doc']['artboards'][0]
    for name in ['idle','walk']:
        assert next(a for a in old_art['animations'] if a['props']['name']==name)==next(a for a in art['animations'] if a['props']['name']==name)
    r=session.put(base+'/api/projects/'+project,json={'doc':json.dumps(doc),'expectedUpdatedAt':snap['meta']['updatedAt']},timeout=90)
    r.raise_for_status()
    diagnostic=call('diagnose_project',{'project':project})
    (qa/'openrive-diagnostics.json').write_text(json.dumps(diagnostic,indent=2))
    assert diagnostic['valid'],diagnostic
    result=call('export_riv',{'project':project})
    (ROOT/'co_di_bo.riv').write_bytes(base64.b64decode(result['dataBase64']))
    (ROOT/'openrive-project.json').write_text(json.dumps(snapshot()['doc'],indent=2))
    result=call('get_project',{'project':project})
    (qa/'openrive-inspect.json').write_text(json.dumps(result,indent=2))
    print('Diagnostics:',json.dumps(diagnostic),flush=True)
    print(meta['editor_url'],flush=True)


if __name__=='__main__':main()
