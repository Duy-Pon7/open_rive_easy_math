"""Replace the existing project's animation with the verified reveal build."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,base64,json,sys
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'huy_di_bo/tools'))
from openrive_client import OpenRive

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--imported-project',required=True);args=parser.parse_args()
    meta_path=ROOT/'openrive.json';meta=json.loads(meta_path.read_text(encoding='utf8'))
    url=urlsplit(meta['editor_url']);base=f'{url.scheme}://{url.netloc}'
    client=OpenRive(base);project=meta['project_id']
    before=client.snapshot(project);imported=client.snapshot(args.imported_project)
    (ROOT/'verification/before_rigid_recoil/live-snapshot.json').write_text(json.dumps(before,indent=2),encoding='utf8')
    response=client.session.put(base+'/api/projects/'+project,json={
        'doc':json.dumps(imported['doc']),'name':'Redo - Retract and Advance',
        'expectedUpdatedAt':before['meta']['updatedAt']},timeout=120)
    response.raise_for_status()
    result=client.call('diagnose_project',{'project':project})
    (ROOT/'verification/openrive-diagnostics.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    assert result['valid'] and not result['diagnostics'],result
    exported=client.call('export_riv',{'project':project})
    content=base64.b64decode(exported['dataBase64'])
    assert content==(ROOT/'redo.riv').read_bytes(),'Export differs from verified local file'
    snapshot=client.snapshot(project)
    (ROOT/'openrive-project.json').write_text(json.dumps(snapshot['doc'],indent=2),encoding='utf8')
    inspected=client.call('get_project',{'project':project})
    (ROOT/'verification/openrive-inspect.json').write_text(json.dumps(inspected,indent=2),encoding='utf8')
    meta.update(reveal='moving-head-with-growing-trail',icon_rotation_degrees=0,end_motion='rigid head retracts along arc, shortening trail, then advances to rest',head_deformation=False)
    meta_path.write_text(json.dumps(meta,indent=2),encoding='utf8')
    print(json.dumps({'editor':meta['editor_url'],'name':snapshot['meta']['name'],'diagnostics':result},indent=2))

if __name__=='__main__':main()
