"""Compare every exported right-facing jump frame with the original reflected."""
import json
import io
import threading
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from playwright.sync_api import sync_playwright
from check_rabbit import decode, white
from serve_rabbit import ROOT, server


def error(a,b):
    return float(np.abs(np.asarray(white(a),dtype=float)-np.asarray(white(b),dtype=float)).mean())


def main():
    qa=ROOT/'verification/right'
    qa.mkdir(exist_ok=True,parents=True)
    app=server()
    threading.Thread(target=app.serve_forever,daemon=True).start()
    results=[]
    def check(name,passed,**details):
        results.append({'test':name,'passed':bool(passed),**details})
        print(name,'PASS' if passed else 'FAIL',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':914,'height':880},device_scale_factor=1)
        page.goto((ROOT/'contho914x880.svg').as_uri())
        # Browser screenshots render the SVGs with their exact intrinsic canvas.
        source=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        page.goto((ROOT/'contho914x880_right.svg').as_uri())
        right_svg=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')
        right_svg.save(qa/'svg-right.png')
        svg_error=error(ImageOps.mirror(source),right_svg)
        check('svg_is_horizontal_reflection',svg_error<.05,mean_rgb_error=svg_error,canvas=list(right_svg.size))
        url=f'http://127.0.0.1:{app.server_port}/preview.html'
        page.goto(url)
        right_page=browser.new_page(viewport={'width':914,'height':1100})
        right_page.goto(url+'?direction=right')
        for tab in [page,right_page]:
            tab.wait_for_function('window.ready || window.failure')
            assert tab.evaluate('window.failure') is None
        contracts=[tab.evaluate('rabbit.fresh()') for tab in [page,right_page]]
        check('controller_inputs_preserved',contracts[0]==contracts[1]==['jump','reset'])
        for tab in [page,right_page]:tab.evaluate('rabbit.advance(.1)')
        idle=decode(right_page.evaluate('rabbit.draw()'))
        idle.save(qa/'idle.png')
        ref=Image.new('RGBA',(914,1100))
        ref.paste(right_svg,(0,220))
        idle_error=error(ref,idle)
        check('right_riv_matches_right_svg',idle_error<.05,mean_rgb_error=idle_error)
        for tab in [page,right_page]:tab.evaluate('rabbit.fresh();rabbit.fire("jump");rabbit.advance(0)')
        frames=[];errors=[];same_events=True
        for f in range(85):
            if f:
                for tab in [page,right_page]:tab.evaluate('rabbit.advance(1/60)')
            left=decode(page.evaluate('rabbit.draw()'))
            right=decode(right_page.evaluate('rabbit.draw()'))
            frames.append(right)
            errors.append(error(ImageOps.mirror(left),right))
            same_events &= page.evaluate('rabbit.events()')==right_page.evaluate('rabbit.events()')
        check('all_85_frames_match_mirrored_original',max(errors)<.05,max_mean_rgb_error=max(errors),frames=len(errors))
        check('state_timing_preserved',same_events,events=right_page.evaluate('rabbit.events()'))
        bounds=[im.getchannel('A').getbbox() for im in frames]
        check('no_clipping',all(b and b[0]>0 and b[1]>0 and b[2]<914 and b[3]<1100 for b in bounds))
        right_page.evaluate('rabbit.advance(.15)')
        settled=decode(right_page.evaluate('rabbit.draw()'))
        check('returns_to_idle',np.array_equal(np.array(idle),np.array(settled)) and 'idle' in right_page.evaluate('rabbit.events()'))
        right_page.evaluate('rabbit.fire("jump");rabbit.advance(.45);rabbit.fire("reset");rabbit.advance(.15)')
        check('reset_during_jump',np.array_equal(np.array(idle),np.array(decode(right_page.evaluate('rabbit.draw()')))))
        sheet=Image.new('RGB',(1464,334),'#f5f0f4')
        for i,f in enumerate([0,12,20,37,61,84]):
            sheet.paste(white(frames[f]).resize((244,294)),(i*244,0))
            ImageDraw.Draw(sheet).text((i*244+12,306),f'{f/60:.2f}s',fill='#503e52')
        sheet.save(ROOT/'rabbit_jump_right_states.png')
        gif=[white(im).resize((365,440)) for im in frames[::2]]
        gif += [white(idle).resize((365,440))]*12
        gif[0].save(ROOT/'rabbit_jump_right_demo.gif',save_all=True,append_images=gif[1:],duration=33,loop=0,disposal=2)
        browser.close()
    app.shutdown()
    (qa/'runtime_validation.json').write_text(json.dumps(results,indent=2))
    if not all(result['passed'] for result in results):raise SystemExit(1)


if __name__=='__main__':
    main()
