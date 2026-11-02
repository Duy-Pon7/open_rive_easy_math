"""Exercise the exported Rive file and render idle/playing previews."""
from pathlib import Path
import base64
import io
import json
import threading
import time
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from serve_speaker import server, ROOT

QA=ROOT/'verification'

def decode(value):
    return Image.open(io.BytesIO(base64.b64decode(value.split(',')[1]))).convert('RGBA')

def yellow(im):
    p=np.asarray(im).astype(float)
    return int(np.count_nonzero((p[:,:,0]>p[:,:,2]+70)&(p[:,:,1]>p[:,:,2]+70)&(p[:,:,3]>30)))

def main():
    app=server()
    threading.Thread(target=app.serve_forever,daemon=True).start()
    results=[]
    def check(name, passed, **extra):
        results.append(dict(test=name,passed=bool(passed),**extra))
        print(name,bool(passed),flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport=dict(width=1100,height=800))
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure',timeout=30000)
        assert page.evaluate('window.failure') is None, page.evaluate('window.failure')
        page.wait_for_timeout(250)
        check('default_is_idle', page.evaluate('speaker.value()') is False and 'idle' in page.evaluate('speaker.events()'))
        idle=decode(page.evaluate('speaker.draw()'));idle.save(QA/'idle.png')
        page.wait_for_timeout(250)
        still=decode(page.evaluate('speaker.draw()'))
        check('idle_is_stationary', np.array_equal(np.array(idle),np.array(still)))
        check('idle_rays_are_hidden',yellow(idle)==0,yellow_pixels=yellow(idle))
        page.click('#play')
        page.wait_for_timeout(320)
        check('boolean_enters_playing','playing' in page.evaluate('speaker.events()'))
        frames=[]
        for i in range(12):
            frames.append(decode(page.evaluate('speaker.draw()')))
            page.wait_for_timeout(100)
        frames[0].save(QA/'playing.png')
        check('playing_rays_are_visible',min(map(yellow,frames))>1000,yellow_pixels=list(map(yellow,frames)))
        check('playing_visibly_animates',len({im.tobytes() for im in frames})==len(frames))
        check('all_frames_fit_canvas',all(im.getchannel('A').getbbox() and 0<im.getchannel('A').getbbox()[0]<im.getchannel('A').getbbox()[2]<627 and 0<im.getchannel('A').getbbox()[1]<im.getchannel('A').getbbox()[3]<627 for im in [idle,*frames]))
        page.wait_for_timeout(2500)
        check('playing_continues_after_multiple_loops',page.evaluate('speaker.value()') is True and yellow(decode(page.evaluate('speaker.draw()')))>1000)
        page.click('#idle');page.wait_for_timeout(350)
        returned=decode(page.evaluate('speaker.draw()'));returned.save(QA/'returned_idle.png')
        check('stop_returns_to_exact_idle',np.array_equal(np.array(returned),np.array(idle)),events=page.evaluate('speaker.events()'))
        for i in range(3):
            page.click('#play');page.wait_for_timeout(60);page.click('#idle');page.wait_for_timeout(250)
        check('rapid_toggle_returns_to_idle',yellow(decode(page.evaluate('speaker.draw()')))==0 and page.evaluate('speaker.value()') is False)
        check('no_runtime_errors',not errors,errors=errors)
        page.screenshot(path=str(QA/'preview.png'))
        browser.close()
    # Preserve transparency in individual frames; use a white contact sheet.
    sheet=Image.new('RGB',(1254,680),'white');draw=ImageDraw.Draw(sheet)
    sheet.paste(idle,(0,35),idle);sheet.paste(frames[0],(627,35),frames[0])
    draw.text((24,12),'IDLE',fill='#153e58');draw.text((651,12),'PLAYING',fill='#153e58')
    sheet.save(ROOT/'loa_doc_states.png')
    gif=[]
    for im in frames:
        bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im)
        gif.append(bg.convert('RGB').resize((400,400)))
    gif[0].save(ROOT/'loa_doc_demo.gif',save_all=True,append_images=gif[1:],duration=100,loop=0)
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2))
    app.shutdown()
    assert all(r['passed'] for r in results), results

if __name__=='__main__':
    main()
