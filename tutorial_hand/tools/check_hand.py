"""Render and exercise the delivered .riv using the bundled WASM runtime."""
from pathlib import Path
import base64,io,json,threading
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from serve_hand import server,ROOT
from motion import BASE_Y, HEIGHT, PRESS_DEPTH, RELEASE_LIFT, RELEASE_APEX_FRAME

QA=ROOT/'verification'
def decode(url):return Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGBA')

def white_pixels(im):
    bg=Image.new('RGBA',im.size,'white')
    return np.array(Image.alpha_composite(bg,im).convert('RGB')).astype(float)

def cap_matches(original,pressed):
    a=original[:,:,3]>127;b=pressed[:,:,3]>127
    return np.count_nonzero(a&b)/np.count_nonzero(a|b)>.99

def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    results=[]
    def check(name,passed,**extra):
        results.append(dict(test=name,passed=bool(passed),**extra));print(name,bool(passed),flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        page=browser.new_page(viewport={'width':1000,'height':740},device_scale_factor=1)
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        page.screenshot(path=str(QA/'preview.png'))
        contract=page.evaluate('hand.fresh()')
        check('input_contract',contract=={'input':'is_pressed','value':False},contract=contract)
        rest=decode(page.evaluate('hand.draw()'));rest.save(QA/'idle.png')
        down=decode(page.evaluate('()=>{hand.set(true);hand.advance(.3);return hand.draw();}'));down.save(QA/'press_mid.png')
        check('press_still_moving_after_300ms','hold' not in page.evaluate('hand.events()'))
        outside_index=np.ones((HEIGHT,227),dtype=bool)
        outside_index[:81,97:133]=False
        held=decode(page.evaluate('()=>{hand.advance(.8);return hand.draw();}'));held.save(QA/'hold.png')
        check('press_reaches_hold', 'press_down' in page.evaluate('hand.events()') and 'hold' in page.evaluate('hand.events()'),events=page.evaluate('hand.events()'))
        # Rive retessellates the contour when a vertex moves. Allow only tiny
        # antialias differences on stationary edges; their geometry stays fixed.
        body_error=float(np.abs(white_pixels(held)-white_pixels(rest))[outside_index].mean())
        check('palm_and_other_fingers_stationary',body_error<.05,mean_rgb_error=body_error)
        cap_before=np.array(rest)[4:16,97:130]
        cap_pressed=np.array(held)[18:30,97:130]
        check('round_fingertip_preserved_on_press',cap_matches(cap_before,cap_pressed))
        top_before=rest.getchannel('A').getbbox()[1]
        top_pressed=held.getchannel('A').getbbox()[1]
        check('shallower_14px_press',top_pressed-top_before==PRESS_DEPTH,depth_px=top_pressed-top_before)
        later=decode(page.evaluate('()=>{hand.advance(8);return hand.draw();}'))
        check('hold_stays_exactly_still_8_seconds',np.array_equal(np.array(held),np.array(later)))
        release=decode(page.evaluate('()=>{hand.set(false);hand.advance(.2);return hand.draw();}'));release.save(QA/'release_mid.png')
        check('release_still_moving_after_200ms',page.evaluate('hand.events().at(-1)')=='release_up')
        end=decode(page.evaluate('()=>{hand.advance(.8);return hand.draw();}'));end.save(QA/'released.png')
        check('release_returns_original_pose',np.array_equal(np.array(rest),np.array(end)),events=page.evaluate('hand.events()'))
        check('visibly_distinct_press_hold_release',len({im.tobytes() for im in [rest,down,held,release]})==4)
        quick=page.evaluate('()=>{hand.fresh();hand.set(true);hand.advance(.05);hand.set(false);hand.advance(.9);return hand.snapshot();}')
        check('release_during_press_returns_idle',np.array_equal(np.array(decode(quick['image'])),np.array(rest)),events=quick['events'])
        again=page.evaluate('()=>{hand.fresh();hand.set(true);hand.advance(.8);hand.set(false);hand.advance(.07);hand.set(true);hand.advance(.8);return hand.snapshot();}')
        check('repress_during_release_reaches_hold',np.array_equal(np.array(decode(again['image'])),np.array(held)),events=again['events'])
        cycle=page.evaluate('()=>{hand.fresh();for(let i=0;i<20;i++){hand.set(true);hand.advance(.8);hand.set(false);hand.advance(.8);}return hand.snapshot();}')
        check('20_repeated_cycles_restore_idle',np.array_equal(np.array(decode(cycle['image'])),np.array(rest)))
        for name,t in [('press_down',.6),('hold',.5),('release_up',0)]:
            pose=decode(page.evaluate('([n,t])=>hand.pose(n,t)',[name,t]))
            check('timeline_boundary_'+name,np.array_equal(np.array(pose),np.array(held)))
        mid=decode(page.evaluate('hand.pose("press_down",.3)'))
        check('palm_stationary_at_mid_press',np.abs(white_pixels(mid)-white_pixels(rest))[outside_index].mean()<.05)
        cap_mid=np.array(mid)[11:23,97:130]
        check('round_fingertip_preserved_at_mid_press',cap_matches(cap_before,cap_mid))
        lift=decode(page.evaluate('(t)=>hand.pose("release_up",t)',RELEASE_APEX_FRAME/60))
        lift.save(QA/'release_lift.png')
        top_lift=lift.getchannel('A').getbbox()[1]
        check('release_lifts_2px_before_settling',top_before-top_lift==RELEASE_LIFT and top_lift>0,lift_px=top_before-top_lift)
        check('release_lift_preserves_round_tip',cap_matches(cap_before,np.array(lift)[2:14,97:130]))
        check('palm_stationary_during_release_lift',np.abs(white_pixels(lift)-white_pixels(rest))[outside_index].mean()<.05)
        settled=decode(page.evaluate('hand.pose("release_up",.6)'))
        check('release_settles_exactly_at_rest',np.array_equal(np.array(settled),np.array(rest)))
        # Animated preview comes from the same state machine as the delivered file.
        page.evaluate('hand.fresh()');frames=[]
        for i in range(96):
            if i==8:page.evaluate('hand.set(true)')
            if i==58:page.evaluate('hand.set(false)')
            frame=decode(page.evaluate('()=>{hand.advance(1/30);return hand.draw();}'))
            bg=Image.new('RGBA',frame.size,'#eef4f8');bg.alpha_composite(frame)
            frames.append(bg.convert('RGB'))
        frames[0].save(ROOT/'tutorial_hand_demo.gif',save_all=True,append_images=frames[1:],duration=33,loop=0,disposal=2)
        # Compare to the actual SVG rasterized by Chromium at its original canvas size.
        page.set_viewport_size({'width':227,'height':368});page.goto((ROOT/'tutorial_hand.svg').as_uri())
        page.screenshot(path=str(QA/'source.png'),omit_background=True)
        original=Image.open(QA/'source.png').convert('RGBA').crop((0,-BASE_Y,227,342))
        def onwhite(im):
            bg=Image.new('RGBA',im.size,'white');return np.array(Image.alpha_composite(bg,im).convert('RGB')).astype(float)
        mae=float(np.abs(onwhite(original)-onwhite(rest)).mean())
        check('idle_preserves_original_svg',mae<1,mean_rgb_error=mae)
        # Assemble comparison sheet from verified runtime frames.
        sheet=Image.new('RGB',(227*6,HEIGHT+41),'#eef4f8');d=ImageDraw.Draw(sheet)
        for i,(label,im) in enumerate([('Idle',rest),('Gentle press',down),('Hold',held),('Release up',release),('Light lift',lift),('Settled',end)]):
            sheet.paste(im,(i*227,40),im);d.text((i*227+20,15),label,fill='#15354b')
        sheet.save(ROOT/'tutorial_hand_states.png')
        browser.close()
    app.shutdown()
    (QA/'runtime_validation.json').write_text(json.dumps(results,indent=2))
    assert all(r['passed'] for r in results),[r for r in results if not r['passed']]

if __name__=='__main__':main()
