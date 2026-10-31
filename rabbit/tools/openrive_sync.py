"""Author jump keyframes through the local OpenRive MCP and export the result."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]


def profile(points, frame):
    for (a, va), (b, vb) in zip(points, points[1:]):
        if frame <= b:
            u = max(0, (frame-a)/(b-a))
            u = u*u*(3-2*u)
            return va+(vb-va)*u
    return points[-1][1]


def tracks():
    data = {
        ('RabbitRoot','x'): [(0,520),(84,520)],
        ('RabbitRoot','scaleX'): [(0,1),(12,1.10),(17,.94),(35,1.01),(55,.97),(61,1.11),(72,.99),(84,1)],
        ('RabbitRoot','scaleY'): [(0,1),(12,.86),(17,1.06),(35,.99),(55,1.035),(61,.86),(72,1.015),(84,1)],
        ('RabbitRoot','rotationDegrees'): [(0,0),(12,-1),(19,2),(35,1),(55,-1),(62,0),(84,0)],
        ('Head','rotationDegrees'): [(0,0),(12,-3),(21,2),(36,0),(55,-2),(64,2),(74,-.7),(84,0)],
        ('FrontEar','rotationDegrees'): [(0,0),(13,7),(20,-10),(34,-3),(50,4),(59,12),(67,-7),(76,3),(84,0)],
        ('RearEar','rotationDegrees'): [(0,0),(14,5),(22,-8),(36,-2),(52,3),(61,9),(69,-5),(78,2),(84,0)],
        ('Tail','rotationDegrees'): [(0,0),(12,8),(22,-8),(37,0),(57,5),(65,-6),(76,2),(84,0)],
        ('Eye','scaleY'): [(0,1),(8,1),(11,.12),(14,1),(56,1),(60,.25),(64,1),(84,1)],
    }
    result = {}
    for (obj, prop), points in data.items():
        result[obj,prop] = [profile(points,f) for f in range(85)]
    # Exact ballistic arc between takeoff and contact; squash keeps feet planted.
    result['RabbitRoot','y'] = [1044-190*4*((f-17)/40)*(1-(f-17)/40) if 17<f<57 else 1044 for f in range(85)]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    args = parser.parse_args()
    session = requests.Session()
    session.headers['Accept'] = 'application/json, text/event-stream'
    url = args.base+'/api/mcp'
    r = session.post(url, json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'rabbit-jump-builder','version':'1'}}}, timeout=30)
    r.raise_for_status()
    session.headers['mcp-session-id'] = r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30)

    def call(name, arguments):
        r = session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=120)
        r.raise_for_status()
        payload = r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):
            raise RuntimeError(payload)
        result = payload['result']
        structured = result.get('structuredContent',{})
        return structured.get('result') if 'result' in structured else json.loads(result['content'][0]['text'])

    meta_path = ROOT/'openrive.json'
    if meta_path.exists():
        project = json.loads(meta_path.read_text())['project_id']
    else:
        imported = call('import_riv',{'name':'Rabbit - Jump','dataBase64':base64.b64encode((ROOT/'rabbit_jump.riv').read_bytes()).decode()})
        project = imported.get('id') or imported.get('projectId') or imported.get('project',{}).get('id')
        if not project:
            raise RuntimeError(imported)
        meta_path.write_text(json.dumps({'project_id':project,'base_url':args.base,'editor_url':args.base+'/editor/'+project},indent=2))
    ops = []
    for (obj, prop), values in tracks().items():
        ops.append({'op':'add_keyframes','timeline':'jump','object':obj,'property':prop,
                    'keys':[{'frame':f,'value':round(value,7),'ease':'linear'} for f,value in enumerate(values)]})
        ops.append({'op':'add_keyframes','timeline':'idle','object':obj,'property':prop,
                    'keys':[{'frame':0,'value':values[0],'ease':'linear'},{'frame':60,'value':values[0],'ease':'linear'}]})
    result = call('apply_edit_plan',{'project':project,'operations':ops})
    (ROOT/'verification/jump-keyframes-mcp.json').write_text(json.dumps(result,indent=2))
    for name, file in [('get_project','openrive-inspect.json'),('diagnose_project','openrive-diagnostics.json')]:
        result = call(name,{'project':project})
        (ROOT/'verification'/file).write_text(json.dumps(result,indent=2))
        if name == 'diagnose_project':
            print('Diagnostics:',json.dumps(result),flush=True)
    exported = call('export_riv',{'project':project})
    data = base64.b64decode(exported['dataBase64'])
    (ROOT/'rabbit_jump.riv').write_bytes(data)
    r = session.get(args.base+'/api/projects/'+project,timeout=30)
    r.raise_for_status()
    (ROOT/'openrive-project.json').write_text(json.dumps(r.json()['doc'],indent=2))
    (ROOT/'verification/export.json').write_text(json.dumps({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},indent=2))
    print(args.base+'/editor/'+project,flush=True)


if __name__ == '__main__':
    main()
