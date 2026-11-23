"""Keep both existing OpenRive links while installing color-bound files."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,base64,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'huy_di_bo/tools'))
from openrive_client import OpenRive

def main():
    p=argparse.ArgumentParser();p.add_argument('--tick',required=True);p.add_argument('--redo',required=True);args=p.parse_args()
    for name in ['tick','redo']:
        folder=ROOT/name;meta_path=folder/'openrive.json';meta=json.loads(meta_path.read_text(encoding='utf8'))
        url=urlsplit(meta['editor_url']);client=OpenRive(f'{url.scheme}://{url.netloc}')
        target=meta['project_id'];before=client.snapshot(target);candidate=client.snapshot(getattr(args,name))
        backup=folder/'verification/before_color/live-snapshot.json'
        if not backup.exists():backup.write_text(json.dumps(before,indent=2),encoding='utf8')
        client.update(target,candidate['doc'],before['meta']['updatedAt'])
        diagnostics=client.call('diagnose_project',{'project':target})
        assert diagnostics['valid'] and not any(d.get('severity')=='error' for d in diagnostics['diagnostics']),diagnostics
        exported=client.call('export_riv',{'project':target})
        assert base64.b64decode(exported['dataBase64'])==(folder/(name+'.riv')).read_bytes()
        inspected=client.call('get_project',{'project':target})
        snapshot=client.snapshot(target)
        (folder/'openrive-project.json').write_text(json.dumps(snapshot['doc'],indent=2),encoding='utf8')
        (folder/'verification/openrive-diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf8')
        (folder/'verification/openrive-inspect.json').write_text(json.dumps(inspected,indent=2),encoding='utf8')
        meta.update(view_model='IconStyle',color_property='iconColor',default_color='#0D99FF')
        meta_path.write_text(json.dumps(meta,indent=2),encoding='utf8')
        print(json.dumps({'icon':name,'editor':meta['editor_url'],'valid':diagnostics['valid'],'byte_identical':True}),flush=True)

if __name__=='__main__':main()
