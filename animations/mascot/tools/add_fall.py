"""Build native vector Fall animation through the local OpenRive MCP."""
import base64
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
from svgpathtools import CubicBezier, Line, parse_path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = 'rMJxzt1_oO6E'
BASE = 'http://127.0.0.1:59146'
session = requests.Session()
session.headers.update({'Accept': 'application/json, text/event-stream'})
response = session.post(BASE + '/api/mcp', json={
    'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
    'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
               'clientInfo': {'name': 'mascot-fall-builder', 'version': '1.0'}}})
response.raise_for_status()
session.headers['mcp-session-id'] = response.headers['mcp-session-id']
session.post(BASE + '/api/mcp', json={'jsonrpc': '2.0', 'method': 'notifications/initialized'})


def call(name, arguments):
    response = session.post(BASE + '/api/mcp', json={
        'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
        'params': {'name': name, 'arguments': arguments}})
    response.raise_for_status()
    payload = response.json()
    if 'error' in payload:
        raise RuntimeError(payload)
    payload = payload['result']
    if payload.get('isError'):
        raise RuntimeError(payload)
    if 'result' in payload and isinstance(payload['result'], dict) and payload['result'].get('isError'):
        raise RuntimeError(payload)
    return payload


def result(payload):
    return payload.get('structuredContent', {}).get('result') or json.loads(payload['content'][0]['text'])


def apply(operations):
    for start in range(0, len(operations), 90):
        call('apply_edit_plan', {'project': PROJECT, 'operations': operations[start:start + 90]})
        print('Applied', start, min(start + 90, len(operations)), flush=True)


def export():
    data = result(call('export_riv', {'project': PROJECT}))
    content = base64.b64decode(data['dataBase64'])
    (ROOT / 'mascot_run_fall.riv').write_bytes(content)
    doc = requests.get(BASE + '/api/projects/' + PROJECT).json()['doc']
    (ROOT / 'openrive-project.json').write_text(json.dumps(doc, indent=2), encoding='utf8')
    print('Exported', len(content), 'bytes', flush=True)


def vector(name, segments, fill, parent, origin):
    ox, oy = origin
    points = []
    def point(z):
        return {'x': round(z.real - ox, 5), 'y': round(z.imag - oy, 5)}
    for seg in segments:
        if not points:
            points.append(point(seg.start))
        if isinstance(seg, CubicBezier):
            points[-1].update(outX=round((seg.control1 - seg.start).real, 5),
                              outY=round((seg.control1 - seg.start).imag, 5))
        end = point(seg.end)
        if isinstance(seg, CubicBezier):
            end.update(inX=round((seg.control2 - seg.end).real, 5),
                       inY=round((seg.control2 - seg.end).imag, 5))
        points.append(end)
    if abs(segments[-1].end - segments[0].start) < .002:
        last = points.pop()
        points[0].update({key: value for key, value in last.items() if key.startswith('in')})
    return {'op': 'add_path', 'name': name, 'parent': parent,
            'points': points, 'closed': True, 'fill': fill}


def build():
    snapshot = requests.get(BASE + '/api/projects/' + PROJECT).json()
    if any(t['props']['name'] == 'Fall' for t in snapshot['doc']['artboards'][0]['animations']):
        raise RuntimeError('Fall already exists. Use focused edits rather than rebuilding.')
    operations = []
    def group(name, x=0, y=0, parent=None, opacity=1):
        operations.append({'op': 'add_group', 'name': name, 'x': x, 'y': y,
                           **({'parent': parent} if parent else {})})
        if opacity != 1:
            operations.append({'op': 'set_properties', 'object': name, 'properties': {'opacity': opacity}})
    group('Fall Scene', opacity=0)
    group('Fall Character', 543, 1000, 'Fall Scene')
    group('Water Splash', 800, 1250, 'Fall Scene')
    group('Motion Trail', 0, 0, 'Fall Scene')
    group('Released Balloon', 930, 750, 'Fall Scene')
    svg = ET.parse(ROOT / 'fall.svg').getroot()
    water = set(range(29, 38)) | {39, 42} | set(range(44, 51))
    for i, element in enumerate(svg):
        if i in water:
            parent, origin = 'Water Splash', (800, 1250)
        elif i in {41, 43}:
            parent, origin = 'Motion Trail', (0, 0)
        else:
            parent, origin = 'Fall Character', (543, 1000)
        operations.append(vector('fall_svg_%02d' % i, list(parse_path(element.attrib['d'])),
                                 element.attrib['fill'], parent, origin))
    # Reconstruct the portion originally occluded by the hand, so the balloon is whole in flight.
    run = ET.parse(ROOT / 'run.svg').getroot()
    source = list(parse_path(run[23].attrib['d']))
    body = source[:5] + [
        CubicBezier(source[4].end, 850+823j, 826+790j, source[8].end),
        source[9], source[10]]
    operations.append(vector('Airborne Water Balloon', body, '#4299FD', 'Released Balloon', (930, 750)))
    for i in [24, 25, 32]:
        operations.append(vector('balloon_detail_%02d' % i, list(parse_path(run[i].attrib['d'])),
                                 run[i].attrib['fill'], 'Released Balloon', (930, 750)))
    operations += [
        {'op': 'add_timeline', 'name': 'Fall', 'duration': 1.5, 'fps': 60, 'loop': 'oneShot'},
        {'op': 'add_property', 'name': 'isFalling', 'type': 'boolean', 'value': False},
        {'op': 'add_state', 'stateMachine': 'Run Controller', 'timeline': 'Fall'},
        {'op': 'add_transition', 'stateMachine': 'Run Controller', 'from': 'Run', 'to': 'Fall',
         'durationMs': 80, 'conditions': [{'property': 'isFalling', 'op': '==', 'value': True}]},
        {'op': 'add_transition', 'stateMachine': 'Run Controller', 'from': 'Fall', 'to': 'Run',
         'durationMs': 0, 'conditions': [{'property': 'isFalling', 'op': '==', 'value': False}]},
    ]
    def keys(obj, prop, frames, values, timeline='Fall', ease='easeInOut'):
        operations.append({'op': 'add_keyframes', 'timeline': timeline, 'object': obj,
                           'property': prop, 'keys': [{'frame': f, 'value': v, 'ease': ease}
                                                     for f, v in zip(frames, values)]})
    # Explicit visibility keys reset every overlay on return to the run cycle.
    for name, opacity in [('Runner', 1), ('Fall Scene', 0)]:
        keys(name, 'opacity', [0, 36], [opacity, opacity], 'Run', 'hold')
    keys('Runner', 'opacity', [0, 9, 10, 90], [1, 1, 0, 0], ease='hold')
    keys('Fall Scene', 'opacity', [0, 9, 10, 90], [0, 0, 1, 1], ease='hold')
    keys('Runner', 'rotationDegrees', [0, 6, 10], [2, -6, -12])
    keys('Runner', 'y', [0, 6, 10], [1040, 1025, 1010])
    for name, value in [('Near Leg', -8), ('Far Leg', 8), ('Far Arm', -12), ('Candy Arm', 6), ('Head', -2), ('Tail', 8), ('Bell', -9)]:
        keys(name, 'rotationDegrees', [0, 10], [value, value])
    for name in ['Near Leg', 'Far Leg']:
        keys(name, 'scaleY', [0, 10], [1, 1])
    keys('Head', 'y', [0, 10], [-320, -320])
    keys('Fall Character', 'x', [0, 10, 24, 45, 62, 90], [543, 543, 531, 543, 543, 543])
    keys('Fall Character', 'y', [0, 10, 24, 45, 51, 66, 90], [960, 960, 928, 1000, 986, 1000, 1000])
    keys('Fall Character', 'rotationDegrees', [0, 10, 24, 45, 51, 66, 90], [8, 8, -6, 0, 2, 0, 0])
    keys('Released Balloon', 'opacity', [0, 9, 10, 44, 45, 90], [0, 0, 1, 1, 0, 0], ease='hold')
    keys('Released Balloon', 'x', [0, 10, 22, 34, 45, 90], [945, 945, 909, 855, 800, 800], ease='linear')
    keys('Released Balloon', 'y', [0, 10, 22, 34, 45, 90], [720, 720, 678, 844, 1190, 1190])
    keys('Released Balloon', 'rotationDegrees', [0, 10, 22, 34, 45, 90], [0, 0, -35, -80, -125, -125], ease='linear')
    keys('Released Balloon', 'scaleY', [0, 10, 34, 44, 45, 90], [1, 1, 1.02, 1.12, .5, .5])
    keys('Water Splash', 'opacity', [0, 44, 45, 90], [0, 0, 1, 1], ease='hold')
    keys('Water Splash', 'scaleX', [0, 44, 45, 51, 63, 72, 90], [.2, .2, .25, 1.12, .98, 1, 1])
    keys('Water Splash', 'scaleY', [0, 44, 45, 51, 63, 72, 90], [.08, .08, .14, 1.18, .94, 1, 1])
    keys('Motion Trail', 'opacity', [0, 9, 10, 90], [0, 0, 1, 1], ease='hold')
    # Preserve the reference's exact final geometry while making outer drops burst outward.
    for i in [39, 42, 44, 46, 47, 48, 49, 50]:
        bounds = parse_path(svg[i].attrib['d']).bbox()
        cx, cy = (bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2
        keys('fall_svg_%02d' % i, 'x', [0, 44, 45, 55, 72, 90],
             [(800-cx)*.45, (800-cx)*.45, (800-cx)*.45, (cx-800)*.10, 0, 0])
        keys('fall_svg_%02d' % i, 'y', [0, 44, 45, 55, 72, 90],
             [(1250-cy)*.45, (1250-cy)*.45, (1250-cy)*.45, -16, 0, 0])
    (ROOT / 'fall-edit-plan.json').write_text(json.dumps(operations, indent=2), encoding='utf8')
    apply(operations)
    export()
    diagnostics = result(call('diagnose_project', {'project': PROJECT}))
    (ROOT / 'fall-diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    print(json.dumps(diagnostics))


if __name__ == '__main__':
    build()
