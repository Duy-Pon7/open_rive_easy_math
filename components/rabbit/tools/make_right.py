"""Mirror the supplied SVG and the delivered .riv without changing animation keys."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default=json.loads((ROOT/'openrive.json').read_text())['base_url'])
    args = parser.parse_args()
    qa = ROOT/'verification/right'
    qa.mkdir(parents=True, exist_ok=True)
    originals = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                 for name in ['contho914x880.svg','rabbit_jump.riv']}
    svg = (ROOT/'contho914x880.svg').read_text(encoding='utf8')
    opening = svg.index('>')+1
    closing = svg.rindex('</svg>')
    mirrored = svg[:opening]+'\n<g transform="translate(914 0) scale(-1 1)">\n'+svg[opening:closing]+'</g>\n'+svg[closing:]
    ET.fromstring(mirrored)
    (ROOT/'contho914x880_right.svg').write_text(mirrored,encoding='utf8')

    session = requests.Session()
    session.headers['Accept'] = 'application/json, text/event-stream'
    url = args.base+'/api/mcp'
    r = session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'rabbit-facing-right','version':'1'}}},timeout=30)
    r.raise_for_status()
    session.headers['mcp-session-id'] = r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()

    def call(name, arguments):
        r = session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':arguments}},timeout=120)
        r.raise_for_status()
        payload = r.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):
            raise RuntimeError(payload)
        result = payload['result']
        structured = result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])

    meta_path = ROOT/'openrive_right.json'
    if meta_path.exists():
        project = json.loads(meta_path.read_text())['project_id']
    else:
        result = call('import_riv',{'name':'Rabbit - Jump Right','dataBase64':base64.b64encode((ROOT/'rabbit_jump.riv').read_bytes()).decode()})
        project = result.get('id') or result.get('projectId') or result.get('project',{}).get('id')
        if not project:
            raise RuntimeError(result)
        meta_path.write_text(json.dumps({'project_id':project,'base_url':args.base,'editor_url':args.base+'/editor/'+project},indent=2))
    response = session.get(args.base+'/api/projects/'+project,timeout=30)
    response.raise_for_status()
    before = response.json()['doc']
    if not (qa/'before-mirror-project.json').exists():
        (qa/'before-mirror-project.json').write_text(json.dumps(before,indent=2))
    objects = before['artboards'][0]['objects']
    facing = next((obj for obj in objects if obj['props'].get('name')=='FacingRight'),None)
    if facing is None:
        result = call('add_group',{'project':project,'name':'FacingRight','x':914,'y':0})
        print('Mirror group:',json.dumps(result),flush=True)
        response = session.get(args.base+'/api/projects/'+project,timeout=30)
        response.raise_for_status()
        facing = next(obj for obj in response.json()['doc']['artboards'][0]['objects'] if obj['props'].get('name')=='FacingRight')
    result = call('apply_edit_plan',{'project':project,'operations':[
        {'op':'set_properties','object':facing['id'],'properties':{'x':914,'y':0,'scaleX':-1,'scaleY':1}}
    ]})
    (qa/'mirror-mcp.json').write_text(json.dumps(result,indent=2))
    response = session.get(args.base+'/api/projects/'+project,timeout=30)
    response.raise_for_status()
    snapshot = response.json()
    doc = snapshot['doc']
    # MCP set_properties casts native reference fields to numbers; use the
    # editor's document API for the string parent reference instead.
    actual_root = next(obj for obj in doc['artboards'][0]['objects'] if obj['props'].get('name')=='RabbitRoot')
    actual_root['props']['parentId'] = facing['id']
    response = session.put(args.base+'/api/projects/'+project,json={
        'doc':json.dumps(doc),'expectedUpdatedAt':snapshot['meta']['updatedAt']},timeout=30)
    response.raise_for_status()
    response = session.get(args.base+'/api/projects/'+project,timeout=30)
    response.raise_for_status()
    doc = response.json()['doc']
    actual_root = next(obj for obj in doc['artboards'][0]['objects'] if obj['props'].get('name')=='RabbitRoot')
    assert actual_root['props']['parentId'] == facing['id'], actual_root
    # Neither timelines nor state machines may change during mirroring.
    assert before['artboards'][0]['animations'] == doc['artboards'][0]['animations']
    assert before['artboards'][0]['stateMachines'] == doc['artboards'][0]['stateMachines']
    (ROOT/'openrive-right-project.json').write_text(json.dumps(doc,indent=2))
    diagnostic = call('diagnose_project',{'project':project})
    (qa/'openrive-diagnostics.json').write_text(json.dumps(diagnostic,indent=2))
    assert diagnostic['valid'], diagnostic
    exported = call('export_riv',{'project':project})
    (ROOT/'rabbit_jump_right.riv').write_bytes(base64.b64decode(exported['dataBase64']))
    inspection = call('get_project',{'project':project})
    (qa/'openrive-inspect.json').write_text(json.dumps(inspection,indent=2))
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in originals.items())
    (qa/'mirror-manifest.json').write_text(json.dumps({'original_sha256':originals,'originals_unchanged':True,
        'mirror_transform':{'x':914,'scaleX':-1},'animation_keys_unchanged':True,'controller_unchanged':True},indent=2))
    print('Diagnostics:',json.dumps(diagnostic),flush=True)
    print(args.base+'/editor/'+project,flush=True)


if __name__ == '__main__':
    main()
