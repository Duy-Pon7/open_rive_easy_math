"""Verify closed curved eyelids and blink independence from native walking."""
import json
import threading
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from check_walk import decode,white,error
from serve_walk import ROOT,server

QA=ROOT/'verification'
EYE_REGIONS=[(214,212,272,242),(303,207,352,238)]


def eye_counts(image):
    return [dict(white=int(np.all(np.array(image.crop(box))[:,:,:3]>235,axis=2).sum()),
                 dark=int(np.all(np.array(image.crop(box))[:,:,:3]<70,axis=2).sum())) for box in EYE_REGIONS]


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
        page.evaluate('coWalk.fresh(false);coWalk.advance(.3)')
        opened=decode(page.evaluate('coWalk.draw()'))
        page.evaluate('coWalk.clearEvents();coWalk.blink();coWalk.advance(.12)')
        closed=decode(page.evaluate('coWalk.draw()'));closed.save(QA/'blink-closed.png')
        counts=eye_counts(closed)
        check('closed_eyes_hide_white_and_pupils',all(c['white']==0 and c['dark']>50 for c in counts),eyes=counts)
        dark=np.all(np.array(closed)[:,:,:3]<70,axis=2)
        def avg_y(x0,x1,y0,y1):
            ys=np.where(dark[y0:y1,x0:x1])[0]
            return float(ys.mean()+y0) if len(ys) else -1
        curves=[(avg_y(239,249,218,242),avg_y(217,223,214,236)),
                (avg_y(324,334,218,238),avg_y(307,313,208,231))]
        check('closed_lids_curve_down_like_reference',all(center>edge+3 for center,edge in curves),center_and_edge_y=curves)
        page.evaluate('coWalk.advance(.3)')
        reopened=decode(page.evaluate('coWalk.draw()'))
        check('manual_blink_reopens_to_original',np.array_equal(np.array(opened),np.array(reopened)) and 'blink_once' in page.evaluate('coWalk.events()'))
        page.evaluate('coWalk.fresh(false);coWalk.advance(2.72)')
        automatic=decode(page.evaluate('coWalk.draw()'))
        check('automatic_blink_while_standing',error(closed,automatic)<.005)
        page.evaluate('coWalk.advance(.5)')
        check('automatic_blink_reopens',np.array_equal(np.array(opened),np.array(decode(page.evaluate('coWalk.draw()')))))
        page.evaluate('coWalk.fresh(true);coWalk.advance(.8);coWalk.clearEvents();coWalk.blink();coWalk.advance(.12)')
        during=decode(page.evaluate('coWalk.draw()'));events=page.evaluate('coWalk.events()')
        page.evaluate('coWalk.fresh(true);coWalk.advance(.92)')
        normal=decode(page.evaluate('coWalk.draw()'))
        outside=np.ones((868,489),dtype=bool);outside[190:245,208:279]=False;outside[185:241,298:359]=False
        body_error=float(np.abs(np.array(white(during),dtype=float)-np.array(white(normal),dtype=float))[outside].mean())
        check('blink_does_not_restart_or_change_walking',body_error<.001 and 'walk' not in events and 'idle' not in events,body_mean_rgb_error=body_error,events=events)
        page.evaluate('coWalk.fresh(true);coWalk.advance(2.72)')
        auto_walk=decode(page.evaluate('coWalk.draw()'))
        check('automatic_blink_while_walking',sum(c['white'] for c in eye_counts(auto_walk))==0)
        repeated=True
        for _ in range(5):
            page.evaluate('coWalk.fresh(false);coWalk.advance(.3);coWalk.blink();coWalk.advance(.12)')
            repeated &= error(closed,decode(page.evaluate('coWalk.draw()')))<.005
            page.evaluate('coWalk.advance(.3)')
            repeated &= np.array_equal(np.array(opened),np.array(decode(page.evaluate('coWalk.draw()'))))
        check('repeat_manual_blink',repeated)
        poses=[]
        for f in [0,3,7,18]:poses.append(decode(page.evaluate('f=>coWalk.pose(f/60,"blink_once")',f)))
        sheet=Image.new('RGB',(4*360,194),'#f7f0f5')
        for i,(im,label) in enumerate(zip(poses,['Open','Closing','Closed','Open'])):
            sheet.paste(white(im).crop((205,180,355,250)).resize((360,168)),(i*360,0))
            ImageDraw.Draw(sheet).text((i*360+12,176),label,fill='#533e55')
        sheet.save(ROOT/'co_di_bo_blink_eyes.png')
        gif=[]
        page.evaluate('coWalk.fresh(false);coWalk.advance(.3)')
        for f in range(48):
            if f==6:page.evaluate('coWalk.blink()')
            page.evaluate('coWalk.advance(1/60)')
            gif.append(white(decode(page.evaluate('coWalk.draw()'))).resize((293,521)))
        gif=gif[::2]
        gif[0].save(ROOT/'co_di_bo_blink.gif',save_all=True,append_images=gif[1:],duration=[33,33,34]*8,loop=0,disposal=2)
        browser.close()
    app.shutdown()
    (QA/'blink_validation.json').write_text(json.dumps(results,indent=2))
    if not all(r['passed'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
