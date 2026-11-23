"""Import the native walking rig into OpenRive MCP, diagnose and export."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);args=parser.parse_args()
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream'
    url=args.base+'/api/mcp'
    response=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'co-walk-builder','version':'1'}}},timeout=30)
    response.raise_for_status();session.headers['mcp-session-id']=response.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()
    def call(name,arguments):
        r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=180)
        r.raise_for_status();payload=r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
        result=payload['result'];structured=result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])
    metadata=ROOT/'openrive.json'
    if metadata.exists():project=json.loads(metadata.read_text())['project_id']
    else:
        imported=call('import_riv',{'name':'Co - Walking','dataBase64':base64.b64encode((ROOT/'co_di_bo.riv').read_bytes()).decode()})
        project=imported.get('id') or imported.get('projectId') or imported.get('project',{}).get('id')
        if not project:raise RuntimeError(imported)
    meta={'project_id':project,'base_url':args.base,'editor_url':args.base+'/editor/'+project}
    metadata.write_text(json.dumps(meta,indent=2))
    for name,filename in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result=call(name,{'project':project})
        (ROOT/'verification'/filename).write_text(json.dumps(result,indent=2))
        if name=='diagnose_project':
            assert result['valid'],result
            print('Diagnostics:',json.dumps(result),flush=True)
    result=call('export_riv',{'project':project});data=base64.b64decode(result['dataBase64'])
    before=(ROOT/'co_di_bo.riv').read_bytes()
    (ROOT/'co_di_bo.riv').write_bytes(data)
    (ROOT/'verification/openrive-roundtrip.json').write_text(json.dumps({'bytes':len(data),'byte_identical':data==before,'sha256':hashlib.sha256(data).hexdigest()},indent=2))
    r=session.get(args.base+'/api/projects/'+project,timeout=60);r.raise_for_status()
    (ROOT/'openrive-project.json').write_text(json.dumps(r.json()['doc'],indent=2))
    print(meta['editor_url'],flush=True)


if __name__=='__main__':main()
