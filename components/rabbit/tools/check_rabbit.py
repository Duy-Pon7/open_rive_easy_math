"""Verify the actual exported .riv, controller, reference fidelity and jump bounds."""
import base64
import io
import json
import threading
import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from serve_rabbit import ROOT, server

QA = ROOT/'verification'


def decode(data):
    return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')


def white(im):
    return Image.alpha_composite(Image.new('RGBA',im.size,'white'),im).convert('RGB')


def main():
    app = server()
    threading.Thread(target=app.serve_forever,daemon=True).start()
    results = []
    def check(name, ok, **details):
        results.append(dict(test=name,passed=bool(ok),**details))
        print(name, 'PASS' if ok else 'FAIL',flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge')
        page = browser.new_page(viewport={'width':914,'height':880},device_scale_factor=1)
        page.goto((ROOT/'contho914x880.svg').as_uri())
        source = Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        inputs = page.evaluate('rabbit.fresh()')
        check('runtime_load_and_inputs',set(inputs)=={'jump','reset'},inputs=inputs)
        page.evaluate('rabbit.advance(.1)')
        rest = decode(page.evaluate('rabbit.draw()'))
        rest.save(QA/'idle.png')
        ref = Image.new('RGBA',(914,1100))
        ref.paste(source,(0,220))
        ref.save(QA/'source.png')
        mae = float(np.abs(np.asarray(white(ref),dtype=float)-np.asarray(white(rest),dtype=float)).mean())
        bounds = [im.getchannel('A').getbbox() for im in (ref,rest)]
        # SVG and Rive rasterizers can differ by one antialias pixel at an edge.
        check('original_svg_fidelity',mae<1 and np.max(np.abs(np.array(bounds[0])-np.array(bounds[1])))<=1,rgb_error=mae,alpha_bounds=bounds)
        frames=[]
        page.evaluate('rabbit.fresh();rabbit.fire("jump")')
        for f in range(85):
            if f:page.evaluate('rabbit.advance(1/60)')
            else:page.evaluate('rabbit.advance(0)')
            frames.append(decode(page.evaluate('rabbit.draw()')))
        events=page.evaluate('rabbit.events()')
        bboxes=[im.getchannel('A').getbbox() for im in frames]
        check('jump_trigger_enters_jump','jump' in events,events=events)
        check('flight_has_clear_lift',max(b[3] for b in bboxes)-min(b[3] for b in bboxes)>170,foot_height_range=[min(b[3] for b in bboxes),max(b[3] for b in bboxes)])
        check('no_clipping_during_jump',all(b and b[0]>0 and b[1]>0 and b[2]<914 and b[3]<1100 for b in bboxes),extents=[min(b[0] for b in bboxes),min(b[1] for b in bboxes),max(b[2] for b in bboxes),max(b[3] for b in bboxes)])
        page.evaluate('rabbit.advance(.15)')
        settled=decode(page.evaluate('rabbit.draw()'))
        check('one_shot_returns_to_exact_idle','idle' in page.evaluate('rabbit.events()') and np.array_equal(np.array(rest),np.array(settled)))
        page.evaluate('rabbit.clearEvents();rabbit.fire("jump");rabbit.advance(.4)')
        check('jump_can_fire_again','jump' in page.evaluate('rabbit.events()'))
        page.evaluate('rabbit.fire("reset");rabbit.advance(.15)')
        reset=decode(page.evaluate('rabbit.draw()'))
        check('reset_mid_jump_returns_to_idle',np.array_equal(np.array(rest),np.array(reset)))
        page.evaluate('rabbit.fresh();rabbit.fire("jump");rabbit.advance(.3);rabbit.fire("jump");rabbit.advance(1.5)')
        check('midair_trigger_does_not_queue_or_restart',page.evaluate('rabbit.events()').count('jump')==1 and np.array_equal(np.array(rest),np.array(decode(page.evaluate('rabbit.draw()')))))
        for label,f in [('anticipation',12),('takeoff',20),('apex',37),('landing',61),('settled',84)]:
            frames[f].save(QA/(label+'.png'))
        selected=[(0,'Đứng'),(12,'Lấy đà'),(20,'Bật lên'),(37,'Trên không'),(61,'Tiếp đất'),(84,'Đứng lại')]
        sheet=Image.new('RGB',(6*244,334),'#f5f0f4')
        for i,(f,label) in enumerate(selected):
            thumb=white(frames[f]).resize((244,294))
            sheet.paste(thumb,(i*244,0))
            # ASCII labels keep the generated contact sheet portable.
            ImageDraw.Draw(sheet).text((i*244+12,306),f'{f/60:.2f}s',fill='#503e52')
        sheet.save(ROOT/'rabbit_jump_states.png')
        gif=[white(im).resize((365,440)) for im in frames[::2]]
        gif += [white(rest).resize((365,440))]*12
        gif[0].save(ROOT/'rabbit_jump_demo.gif',save_all=True,append_images=gif[1:],duration=33,loop=0,disposal=2)
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
