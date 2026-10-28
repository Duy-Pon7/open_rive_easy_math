"""Import the vector rig into OpenRive, diagnose, and export the delivered asset."""
import base64
import json
from pathlib import Path
import argparse
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:57181')
    args = parser.parse_args()
    session = requests.Session()
    session.headers['Accept'] = 'application/json, text/event-stream'
    url = args.base + '/api/mcp'
    init = session.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
        'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                   'clientInfo': {'name': 'loi-character-builder', 'version': '1.0'}}})
    init.raise_for_status()
    session.headers['mcp-session-id'] = init.headers['mcp-session-id']
    session.post(url, json={'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def call(name, arguments):
        response = session.post(url, json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': name, 'arguments': arguments}})
        response.raise_for_status()
        payload = response.json()
        if 'error' in payload or payload.get('result', {}).get('isError'):
            raise RuntimeError(payload)
        result = payload['result']
        return result.get('structuredContent', {}).get('result') or json.loads(result['content'][0]['text'])

    metadata_path = ROOT / 'openrive.json'
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding='utf8'))
        project = metadata['project_id']
    else:
        imported = call('import_riv', {'name': 'Loi - Vietnamese Lip Sync',
            'dataBase64': base64.b64encode((ROOT / 'loi_noi_speaking_vi.riv').read_bytes()).decode()})
        print('Imported:', json.dumps(imported, ensure_ascii=False), flush=True)
        project = imported.get('id') or imported.get('projectId') or imported.get('project', {}).get('id')
        if not project:
            raise RuntimeError(imported)
        metadata = {'project_id': project, 'base_url': args.base,
                    'editor_url': args.base + '/editor/' + project}
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf8')
    inspection = call('get_project', {'project': project})
    (ROOT / 'verification/openrive-inspect.json').write_text(json.dumps(inspection, indent=2), encoding='utf8')
    diagnostics = call('diagnose_project', {'project': project})
    (ROOT / 'verification/openrive-diagnostics.json').write_text(json.dumps(diagnostics, indent=2), encoding='utf8')
    print('Diagnostics:', json.dumps(diagnostics, ensure_ascii=False), flush=True)
    exported = call('export_riv', {'project': project})
    output = base64.b64decode(exported['dataBase64'])
    (ROOT / 'loi_noi_speaking_vi.riv').write_bytes(output)
    snapshot = session.get(args.base + '/api/projects/' + project)
    snapshot.raise_for_status()
    (ROOT / 'openrive-project.json').write_text(json.dumps(snapshot.json()['doc'], indent=2), encoding='utf8')
    print('Exported', len(output), 'bytes;', metadata['editor_url'], flush=True)


if __name__ == '__main__':
    main()
