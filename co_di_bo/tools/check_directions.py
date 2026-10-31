"""Render both directions and check mirroring, state routing and closed eyelids."""
import json
import threading
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from playwright.sync_api import sync_playwright
from check_walk import decode,white,error
from serve_walk import ROOT,server

QA=ROOT/'verification'


def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    results=[]
    def check(name,passed,**details):
        results.append(dict(test=name,passed=bool(passed),**details))
        print(name,'PASS' if passed else 'FAIL',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge');page=browser.new_page()
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure');assert page.evaluate('window.failure') is None
        page.evaluate('coWalk.fresh(false,false);coWalk.advance(.3)')
        idle_right=decode(page.evaluate('coWalk.draw()'))
        page.evaluate('coWalk.fresh(false,true);coWalk.advance(.3)')
        idle_left=decode(page.evaluate('coWalk.draw()'));idle_left.save(QA/'idle-left.png')
        check('idle_left_matches_reflected_original',error(ImageOps.mirror(idle_right),idle_left)<.03,events=page.evaluate('coWalk.events()'))
        errors=[];left_frames=[]
        for f in range(73):
            right=decode(page.evaluate('f=>coWalk.pose(f/60,"walk")',f))
            left=decode(page.evaluate('f=>coWalk.pose(f/60,"walk_left")',f))
            errors.append(error(ImageOps.mirror(right),left));left_frames.append(left)
        # Reversed winding changes antialiasing on fine scarf/cloth contours.
        # This allows under 0.02% of the 8-bit RGB range, across the full frame.
        check('all_73_walk_frames_are_mirrored',max(errors)<.05,max_mean_rgb_error=max(errors))
        doc=json.loads((ROOT/'openrive-project.json').read_text());art=doc['artboards'][0]
        wrapper=next(o for o in art['objects'] if o['props'].get('name')=='FacingRoot')
        def canonical(anim):
            import copy
            value=copy.deepcopy(anim);value['props']['name']='motion'
            value['children']=[c for c in value['children'] if c['props'].get('objectId')!=wrapper['id']]
            def strip_ids(item):
                item.pop('id',None)
                for child in item.get('children',[]):strip_ids(child)
            strip_ids(value);return value
        animations={a['props']['name']:a for a in art['animations']}
        check('all_original_motion_keyframes_preserved',all(canonical(animations[name])==canonical(animations[name+'_left']) for name in ['idle','walk']))
        check('left_walk_not_clipped',all((b:=im.getchannel('A').getbbox()) and b[0]>0 and b[1]>0 and b[2]<489 and b[3]<868 for im in left_frames))
        for walking,left,expected in [(False,False,'idle'),(True,False,'walk'),(False,True,'idle_left'),(True,True,'walk_left')]:
            events=page.evaluate('v=>{coWalk.fresh(v[0],v[1]);coWalk.advance(.4);return coWalk.events();}',[walking,left])
            check('input_routes_to_'+expected,expected in events,events=events)
        page.evaluate('coWalk.fresh(true,true);coWalk.advance(.4);coWalk.clearEvents();coWalk.setWalking(false);coWalk.advance(.4)')
        stopped=decode(page.evaluate('coWalk.draw()'))
        check('left_walk_stops_to_exact_idle',error(stopped,idle_left)<.005 and 'idle_left' in page.evaluate('coWalk.events()'))
        page.evaluate('coWalk.clearEvents();coWalk.setWalking(true);coWalk.advance(.4)')
        check('left_walk_resumes','walk_left' in page.evaluate('coWalk.events()'))
        for walking in [False,True]:
            for facing in [False,True]:
                page.evaluate('v=>{coWalk.fresh(v[0],v[1]);coWalk.advance(.4);coWalk.setFacingLeft(!v[1]);coWalk.advance(.2);}',[walking,facing])
                expected=('walk' if walking else 'idle')+('_left' if not facing else '')
                check('switch_direction_'+str(walking)+'_'+str(facing),expected in page.evaluate('coWalk.events()'))
        page.evaluate('coWalk.fresh(false,false);coWalk.advance(.3);coWalk.blink();coWalk.advance(.12)')
        closed_right=decode(page.evaluate('coWalk.draw()'))
        page.evaluate('coWalk.fresh(false,true);coWalk.advance(.3);coWalk.blink();coWalk.advance(.12)')
        closed_left=decode(page.evaluate('coWalk.draw()'));closed_left.save(QA/'blink-closed-left.png')
        check('manual_blink_and_lid_creases_mirror_left',error(ImageOps.mirror(closed_right),closed_left)<.03)
        page.evaluate('coWalk.fresh(false,true);coWalk.advance(2.72)')
        check('automatic_blink_in_left_idle',error(closed_left,decode(page.evaluate('coWalk.draw()')))<.005)
        page.evaluate('coWalk.fresh(true,false);coWalk.advance(2.72)')
        automatic_right=decode(page.evaluate('coWalk.draw()'))
        page.evaluate('coWalk.fresh(true,true);coWalk.advance(2.72)')
        automatic_left=decode(page.evaluate('coWalk.draw()'))
        check('automatic_blink_in_left_walk',error(ImageOps.mirror(automatic_right),automatic_left)<.03)
        for _ in range(8):page.evaluate('coWalk.setFacingLeft(true);coWalk.setWalking(false);coWalk.advance(.03);coWalk.setFacingLeft(false);coWalk.setWalking(true);coWalk.advance(.03)')
        page.evaluate('coWalk.fresh(false,true);coWalk.advance(.3)')
        check('rapid_switch_keeps_valid_left_idle',error(idle_left,decode(page.evaluate('coWalk.draw()')))<.005)
        sheet=Image.new('RGB',(4*244,464),'#f7f0f5')
        for i,(im,label) in enumerate([(idle_right,'Idle right'),(idle_left,'Idle left'),(left_frames[18],'Walk left'),(closed_left,'Blink left')]):
            sheet.paste(white(im).resize((244,433)),(i*244,0));ImageDraw.Draw(sheet).text((i*244+12,444),label,fill='#533e55')
        sheet.save(ROOT/'co_di_bo_directions.png')
        gif=[white(im).resize((293,521)) for im in left_frames[:-1:2]]
        gif[0].save(ROOT/'co_di_bo_left_demo.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*12,loop=0,disposal=2)
        browser.close()
    app.shutdown()
    (QA/'direction_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
