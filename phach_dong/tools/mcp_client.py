"""Minimal client for the installed OpenRive HTTP MCP server."""
import json
import requests

class OpenRive:
    def __init__(self, base):
        self.base=base
        self.url=base+'/api/mcp'
        self.sequence=1
        self.session=requests.Session()
        self.session.headers['Accept']='application/json, text/event-stream'
        response=self.session.post(self.url,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
            'protocolVersion':'2024-11-05','capabilities':{},
            'clientInfo':{'name':'loa-doc-builder','version':'1'}}},timeout=30)
        response.raise_for_status()
        self.session.headers['mcp-session-id']=response.headers['mcp-session-id']
        self.session.post(self.url,json={'jsonrpc':'2.0','method':'notifications/initialized'},timeout=30).raise_for_status()

    def call(self, name, arguments):
        self.sequence+=1
        response=self.session.post(self.url,json={'jsonrpc':'2.0','id':self.sequence,'method':'tools/call',
            'params':{'name':name,'arguments':arguments}},timeout=120)
        response.raise_for_status()
        payload=response.json()
        if 'error' in payload or payload.get('result',{}).get('isError'):
            raise RuntimeError(payload)
        result=payload['result']
        structured=result.get('structuredContent',{})
        return structured['result'] if 'result' in structured else json.loads(result['content'][0]['text'])

    def snapshot(self, project):
        response=self.session.get(self.base+'/api/projects/'+project,timeout=60)
        response.raise_for_status()
        return response.json()

    def update(self, project, doc, updated_at):
        response=self.session.put(self.base+'/api/projects/'+project,
            json={'doc':json.dumps(doc),'expectedUpdatedAt':updated_at},timeout=120)
        response.raise_for_status()
