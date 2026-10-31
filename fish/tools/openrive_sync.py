"""Import, author native swimming keys through OpenRive MCP, and export."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import requests
from motion import BASE, FRAMES, tracks

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);args=parser.parse_args()
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream'
    url=args.base+'/api/mcp'
    r=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'fish-swim-builder','version':'1'}}},timeout=30)
    r.raise_for_status();session.headers['mcp-session-id']=r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def call(name,arguments):
        r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=120)
        r.raise_for_status();payload=r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
        result=payload['result'];structured=result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])
    meta_path=ROOT/'openrive.json'
    if meta_path.exists():project=json.loads(meta_path.read_text())['project_id']
    else:
        result=call('import_riv',{'name':'Fish - Swim','dataBase64':base64.b64encode((ROOT/'fish_swim.riv').read_bytes()).decode()})
        project=result.get('id') or result.get('projectId') or result.get('project',{}).get('id')
        if not project:raise RuntimeError(result)
    meta={'project_id':project,'base_url':args.base,'editor_url':args.base+'/editor/'+project}
    meta_path.write_text(json.dumps(meta,indent=2))
    r=session.get(args.base+'/api/projects/'+project,timeout=30);r.raise_for_status()
    snapshot=r.json();doc=snapshot['doc'];art=doc['artboards'][0]
    # Keep the existing project, object IDs, state machine, and trigger contract.
    # Put the torso in front of the fin roots, matching the revised RML source.
    objects=art['objects']
    def subtree(obj):
        return [obj]+[desc for child in objects if child['props'].get('parentId')==obj['id'] for desc in subtree(child)]
    ordered=[]
    for name in ['Body','DorsalFin','VentralFin','Tail']:
        ordered.extend(subtree(next(o for o in objects if o['props'].get('name')==name)))
    ids={o['id'] for o in ordered}
    remaining=[o for o in objects if o['id'] not in ids]
    at=next(i for i,o in enumerate(remaining) if o['props'].get('name')=='SVGCoordinates')+1
    art['objects']=remaining[:at]+ordered+remaining[at:]
    swim=next(a for a in art['animations'] if a['props'].get('name')=='swim')
    swim['props']['duration']=FRAMES
    r=session.put(args.base+'/api/projects/'+project,json={'doc':json.dumps(doc),'expectedUpdatedAt':snapshot['meta']['updatedAt']},timeout=30)
    r.raise_for_status()
    ops=[]
    for (name,prop),values in tracks().items():
        ops.append({'op':'add_keyframes','timeline':'swim','object':name,'property':prop,
            'keys':[{'frame':f,'value':round(v,7),'ease':'linear'} for f,v in enumerate(values)]})
        ops.append({'op':'add_keyframes','timeline':'idle','object':name,'property':prop,
            'keys':[{'frame':f,'value':BASE[name,prop],'ease':'linear'} for f in [0,60]]})
    result=call('apply_edit_plan',{'project':project,'operations':ops})
    (ROOT/'verification/swim-keyframes-mcp.json').write_text(json.dumps(result,indent=2))
    for name,filename in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result=call(name,{'project':project})
        (ROOT/'verification'/filename).write_text(json.dumps(result,indent=2))
        if name=='diagnose_project':
            assert result['valid'],result
            print('Diagnostics:',json.dumps(result),flush=True)
    result=call('export_riv',{'project':project});data=base64.b64decode(result['dataBase64'])
    (ROOT/'fish_swim.riv').write_bytes(data)
    r=session.get(args.base+'/api/projects/'+project,timeout=30);r.raise_for_status()
    (ROOT/'openrive-project.json').write_text(json.dumps(r.json()['doc'],indent=2))
    (ROOT/'verification/export.json').write_text(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},indent=2))
    print(meta['editor_url'],flush=True)


if __name__=='__main__':main()
