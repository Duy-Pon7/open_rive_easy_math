"""Import into local OpenRive over MCP, diagnose, render and export."""
import argparse,base64,hashlib,json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);args=parser.parse_args()
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream'
    url=args.base+'/api/mcp'
    response=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'tutorial-hand-builder','version':'1'}}},timeout=30)
    response.raise_for_status();session.headers['mcp-session-id']=response.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30)
    def call(name,arguments):
        r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=120);r.raise_for_status();p=r.json()
        if 'error' in p or p.get('result',{}).get('isError'):raise RuntimeError(p)
        result=p['result'];return result.get('structuredContent',{}).get('result') or json.loads(result['content'][0]['text'])
    meta_path=ROOT/'openrive.json'
    if meta_path.exists():project=json.loads(meta_path.read_text())['project_id']
    else:
        result=call('import_riv',{'name':'Tutorial Hand - Press Hold Release','dataBase64':base64.b64encode((ROOT/'tutorial_hand.riv').read_bytes()).decode()})
        print('Import:',json.dumps(result),flush=True)
        project=result.get('id') or result.get('projectId') or result.get('project',{}).get('id')
        if not project:raise RuntimeError(result)
    meta={'project_id':project,'base_url':args.base,'editor_url':args.base+'/editor/'+project}
    meta_path.write_text(json.dumps(meta,indent=2))
    for name,filename in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result=call(name,{'project':project});(ROOT/'verification'/filename).write_text(json.dumps(result,indent=2))
        if name=='diagnose_project':print('Diagnostics:',json.dumps(result),flush=True)
    r=session.post(url,json={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'render_preview','arguments':{'project':project,'animation':'hold','time':.5,'scale':2}}},timeout=120)
    r.raise_for_status();preview=r.json()
    (ROOT/'verification/openrive-render-response.json').write_text(json.dumps(preview,indent=2))
    if 'error' in preview or preview.get('result',{}).get('isError'):
        print('OpenRive render_preview unavailable; use the verified bundled WASM preview.',flush=True)
    for item in preview.get('result',{}).get('content',[]):
        if item.get('type')=='image':(ROOT/'verification/openrive-hold.png').write_bytes(base64.b64decode(item['data']))
    result=call('export_riv',{'project':project});data=base64.b64decode(result['dataBase64'])
    before=(ROOT/'tutorial_hand.riv').read_bytes()
    (ROOT/'verification/openrive-roundtrip.json').write_text(json.dumps({'byte_identical':data==before,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},indent=2))
    (ROOT/'tutorial_hand.riv').write_bytes(data)
    r=session.get(args.base+'/api/projects/'+project,timeout=30);r.raise_for_status()
    (ROOT/'openrive-project.json').write_text(json.dumps(r.json()['doc'],indent=2))
    print(meta['editor_url'],flush=True)

if __name__=='__main__':main()
