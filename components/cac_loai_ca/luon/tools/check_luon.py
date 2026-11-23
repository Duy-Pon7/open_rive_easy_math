"""Validate native exported vectors, transitions, body wave and loop in Rive WASM."""
import base64
import io
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from scipy.ndimage import label
from serve_luon import ROOT, server

QA = ROOT/'verification'

def decode(value):
    return Image.open(io.BytesIO(base64.b64decode(value.split(',')[1]))).convert('RGBA')

def white(image):
    return Image.alpha_composite(Image.new('RGBA', image.size, 'white'), image).convert('RGB')

def difference(a, b):
    return float(np.abs(np.asarray(white(a), dtype=float)-np.asarray(white(b), dtype=float)).mean())

def main():
    app = server()
    threading.Thread(target=app.serve_forever, daemon=True).start()
    reports = []
    def check(name, passed, **details):
        reports.append(dict(test=name, passed=bool(passed), **details))
        print(name, 'PASS' if passed else 'FAIL', details, flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge')
        page = browser.new_page(viewport={'width':1053, 'height':438}, device_scale_factor=1)
        # Render the source at the exact same scale/offset as the Rive artboard.
        svg = (ROOT.parent/'luon.svg').read_text()
        svg = svg.replace('width="287" height="50"', 'width="861" height="150"')
        page.set_content('<style>body{margin:0}svg{position:absolute;left:96px;top:144px}</style>'+svg)
        reference = Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        reference.save(QA/'source.png')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure', timeout=60000)
        assert page.evaluate('window.failure') is None, page.evaluate('window.failure')
        initial = page.evaluate('eel.fresh();eel.advance(.4);eel.events()')
        check('default_is_idle', 'idle' in initial)
        idle = decode(page.evaluate('eel.draw()')); idle.save(QA/'idle.png')
        mae = difference(reference, idle)
        check('original_svg_fidelity', mae<.6, mean_rgb_error=mae,
              source_bounds=reference.getchannel('A').getbbox(), rive_bounds=idle.getchannel('A').getbbox())
        page.evaluate('eel.advance(2)')
        check('idle_is_still', difference(idle, decode(page.evaluate('eel.draw()')))<.001)
        page.evaluate('eel.setSwim(true);eel.advance(.4)')
        check('idle_to_swim', 'swim' in page.evaluate('eel.events()'))
        frames = []
        for i in range(97):
            if i:
                page.evaluate('eel.advance(1/60)')
            frames.append(decode(page.evaluate('eel.draw()')))
        bounds = [im.getchannel('A').getbbox() for im in frames]
        check('swim_no_clipping', all(b and b[0]>0 and b[1]>0 and b[2]<1053 and b[3]<438 for b in bounds),
              extents=[min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds)])
        check('seamless_swim_loop', difference(frames[0],frames[-1])<.025, mean_rgb_error=difference(frames[0],frames[-1]))
        tail = (90, 130, 410, 350); head = (888, 198, 900, 213)
        tail_change = max(difference(frames[0].crop(tail), im.crop(tail)) for im in frames)
        head_change = max(difference(frames[0].crop(head), im.crop(head)) for im in frames)
        check('tail_wave_with_stable_head', tail_change>3 and head_change<.1, tail_rgb_change=tail_change, head_rgb_change=head_change)
        check('continuous_motion', len({im.tobytes() for im in frames[:-1]})>=90)
        components=[]
        for im in frames[::4]:
            labels,count=label(np.asarray(im)[:,:,3]>100)
            components.append(int(sum(np.bincount(labels.ravel())[1:]>=10)))
        check('body_tail_and_fin_stay_connected', max(components)==1, poses=len(components), max_components=max(components))
        page.evaluate('eel.setSwim(false);eel.advance(.5)')
        stopped = decode(page.evaluate('eel.draw()'))
        check('swim_to_exact_idle', difference(idle,stopped)<.01 and 'idle' in page.evaluate('eel.events()'), mean_rgb_error=difference(idle,stopped))
        page.evaluate('eel.clearEvents();eel.setSwim(true);eel.advance(.5)')
        check('resume_swim', 'swim' in page.evaluate('eel.events()') and difference(idle,decode(page.evaluate('eel.draw()')))>.5)
        for i in range(8):
            page.evaluate('eel.setSwim(false);eel.advance(.08);eel.setSwim(true);eel.advance(.08)')
        page.evaluate('eel.setSwim(false);eel.advance(.6)')
        check('rapid_toggle_recovers_idle', difference(idle,decode(page.evaluate('eel.draw()')))<.01)
        poses = [decode(page.evaluate('(t)=>eel.pose(t)', i*1.6/6)) for i in range(6)]
        sheet = Image.new('RGB', (702, 3*170), '#edf4f2')
        for i, im in enumerate(poses):
            x, y = (i%2)*351, (i//2)*170
            sheet.paste(white(im).resize((351,146)), (x,y))
            ImageDraw.Draw(sheet).text((x+16,y+148), f'swim {i*1.6/6:.2f}s', fill='#183b36')
        sheet.save(ROOT/'luon_states.png')
        gif = [white(im).resize((790,329)) for im in frames[:-1:2]]
        gif[0].save(ROOT/'luon_swim.gif', save_all=True, append_images=gif[1:], duration=([33,33,34]*16), loop=0, disposal=2)
        page.set_viewport_size({'width':1200,'height':920})
        page.reload();page.wait_for_function('window.ready || window.failure')
        page.screenshot(path=str(QA/'preview.png'))
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(reports, indent=2))
    if not all(r['passed'] for r in reports):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
