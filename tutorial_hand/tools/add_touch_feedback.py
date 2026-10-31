"""Add the two reference-colored touch disks to the existing project via MCP."""
import json
from pathlib import Path
import requests
from motion import TOUCH_X,TOUCH_Y

ROOT=Path(__file__).resolve().parents[1]

def main():
    meta=json.loads((ROOT/'openrive.json').read_text())
    base=meta['base_url'];project=meta['project_id']
    r=requests.get(base+'/api/projects/'+project,timeout=15);r.raise_for_status()
    snapshot=r.json()
    backup=ROOT/'verification/before-touch-feedback-project.json'
    if not backup.exists():backup.write_text(json.dumps(snapshot,indent=2))
    if any(o['props'].get('name')=='Touch Feedback' for o in snapshot['doc']['artboards'][0]['objects']):
        print('Touch Feedback already exists');return
    s=requests.Session();s.headers['Accept']='application/json, text/event-stream';url=base+'/api/mcp'
    r=s.post(url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'touch-feedback','version':'1'}}},timeout=20)
    r.raise_for_status();s.headers['mcp-session-id']=r.headers['mcp-session-id'];s.post(url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=20)
    ops=[{'op':'add_group','name':'Touch Feedback','x':TOUCH_X,'y':TOUCH_Y},
         {'op':'add_shape','parent':'Touch Feedback','kind':'ellipse','name':'Touch Inner','x':0,'y':0,'width':44,'height':44,'fill':'#24ADB4'},
         {'op':'add_shape','parent':'Touch Feedback','kind':'ellipse','name':'Touch Outer','x':0,'y':0,'width':68,'height':68,'fill':'#ADE2E5'},
         {'op':'set_properties','object':'Touch Feedback','properties':{'opacity':0,'scaleX':.001,'scaleY':.001}}]
    r=s.post(url,json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'apply_edit_plan','arguments':{'project':project,'operations':ops}}},timeout=30)
    r.raise_for_status();payload=r.json()
    (ROOT/'verification/touch-feedback-mcp.json').write_text(json.dumps(payload,indent=2))
    if 'error' in payload or payload.get('result',{}).get('isError'):raise RuntimeError(payload)
    print('Added native touch disks via OpenRive MCP')

if __name__=='__main__':main()
