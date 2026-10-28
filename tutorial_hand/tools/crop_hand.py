"""Crop the existing OpenRive project's vertical canvas through MCP."""
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]

def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    base=meta['base_url'];project=meta['project_id']
    session=requests.Session();session.headers['Accept']='application/json, text/event-stream'
    url=base+'/api/mcp'
    r=session.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'tutorial-hand-crop','version':'1'}}},timeout=20)
    r.raise_for_status();session.headers['mcp-session-id']=r.headers['mcp-session-id']
    session.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=20)
    response=session.get(base+'/api/projects/'+project,timeout=20);response.raise_for_status()
    doc=response.json()['doc'];art=doc['artboards'][0]
    if art['artboard']['props']['height']==257:
        print('Already cropped');return
    assert art['artboard']['props']['height']==368
    hand=next(o for o in art['objects'] if o['props'].get('name')=='Hand')
    ops=[{'op':'set_properties','object':art['id'],'properties':{'height':257}},
         {'op':'set_properties','object':hand['id'],'properties':{'y':hand['props'].get('y',0)-93}}]
    for anim in art['animations']:
        ko=next(k for k in anim['children'] if k['props'].get('objectId')==hand['id'])
        prop=next(k for k in ko['children'] if k['props'].get('propertyKey')==14)
        keys=[{'frame':k['props'].get('frame',0),'value':k['props'].get('value',0)-93,'ease':'linear'} for k in prop['children']]
        ops.append({'op':'add_keyframes','timeline':anim['id'],'object':hand['id'],'property':'y','keys':keys})
    r=session.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'apply_edit_plan','arguments':{'project':project,'operations':ops}}},timeout=30)
    r.raise_for_status();payload=r.json()
    (ROOT/'verification/crop-mcp-result.json').write_text(json.dumps(payload,indent=2))
    if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
    print('Cropped existing project: 227 x 368 -> 227 x 257; shifted all timelines by -93 px')

if __name__=='__main__':main()
