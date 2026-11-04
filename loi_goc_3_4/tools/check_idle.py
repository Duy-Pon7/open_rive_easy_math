"""Verify idle behavior in the delivered binary using the real WASM runtime."""
import json
import threading
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from check_loi import decode, white
from serve_loi import server, ROOT
from idle_motion import BLINK_STARTS


def eye_ink(im):
    a = np.array(white(im))
    return sum(int(np.all(a[170:216, x0:x1] < 80, axis=2).sum())
               for x0, x1 in [(150, 216), (242, 291)])


def main():
    app = server()
    threading.Thread(target=app.serve_forever, daemon=True).start()
    qa = ROOT/'verification'
    checks = []

    def check(name, passed, **detail):
        checks.append(dict(test=name, status='PASS' if passed else 'FAIL', **detail))
        print(name, checks[-1]['status'], flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge')
        page = browser.new_page(viewport={'width': 1100, 'height': 1000})
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None

        def frame(t, talking=False, manual=False):
            return decode(page.evaluate('''({t,talking,manual})=>{
                loi.fresh();loi.set(0,talking);
                if(manual) {loi.advance(t-.075);loi.fire('blink');loi.advance(.075);}
                else loi.advance(t);
                return loi.draw();
            }''', dict(t=t, talking=talking, manual=manual)))

        rest = frame(0)
        open_ink = eye_ink(rest)
        samples = []
        for start in BLINK_STARTS:
            t = (start+6)/60
            im = frame(t)
            ink = eye_ink(im)
            samples.append(dict(time=t, eye_ink=ink))
            check(f'automatic_blink_at_{t:.2f}s', ink < open_ink*.3, eye_ink=ink)
        reopened = frame((BLINK_STARTS[0]+20)/60)
        check('automatic_blink_reopens', eye_ink(reopened) > open_ink*.85)
        second_cycle = frame(18+(BLINK_STARTS[0]+6)/60)
        check('automatic_blink_repeats_next_cycle', eye_ink(second_cycle) < open_ink*.3)
        manual = frame(.8, manual=True)
        check('manual_blink_works_during_idle', eye_ink(manual) < open_ink*.3)
        check('talking_does_not_use_idle_blinks', eye_ink(frame(3.2, talking=True)) > open_ink*.85)
        resumed = decode(page.evaluate('''()=>{
            loi.fresh();loi.set(2,true);loi.advance(1);loi.set(0,false);loi.advance(3.2);
            return loi.draw();
        }'''))
        check('stop_talking_resumes_automatic_blink', eye_ink(resumed) < open_ink*.3)

        neutral = np.array(rest)
        tilted = np.array(frame(3.7))
        changed = int(np.any(neutral[:160] != tilted[:160], axis=2).sum())
        check('head_moves_without_host_inputs', changed > 300, changed_head_pixels=changed)
        seam = np.array(frame(18))
        delta = np.abs(neutral.astype(float)-seam.astype(float))
        seam_difference = int(np.any(delta, axis=2).sum())
        # The canvas rasterizer can shift a few antialias edge pixels after
        # many floating point advances; require negligible total image error.
        seam_mae = float(delta.mean())
        check('idle_loop_returns_to_neutral', seam_mae < .01 and
              int(np.any(delta > 8, axis=2).sum()) < 100,
              changed_pixels=seam_difference, mean_channel_error=seam_mae)
        # Sequentially advance both animation layers through a full native cycle.
        page.evaluate('loi.fresh()')
        frames = []
        neck_gaps = []
        for _ in range(270):
            im = decode(page.evaluate('()=>{loi.advance(1/15);return loi.draw();}'))
            neck_gaps.append(int((np.array(im)[290:311, 162:204, 3] < 250).sum()))
            frames.append(white(im).resize((200, 499), Image.Resampling.LANCZOS))
        check('neck_stays_connected_through_entire_idle', max(neck_gaps) == 0,
              frames=len(neck_gaps), max_transparent_neck_pixels=max(neck_gaps))
        frames[0].save(ROOT/'loi_goc_3_4_idle_preview.gif', save_all=True,
                       append_images=frames[1:], duration=[67, 67, 66]*90, loop=0)
        # Inspectable stills from the same native machine.
        reopened.save(qa/'idle_eyes_open.png')
        frame(3.2).save(qa/'idle_eyes_closed.png')
        frame(3.7).save(qa/'idle_head_tilt.png')
        browser.close()
    app.shutdown()
    report = dict(checks=checks, failures=sum(x['status']=='FAIL' for x in checks),
                  idle_seconds=18, blink_samples=samples, baseline_eye_ink=open_ink)
    (qa/'idle-runtime-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    assert not report['failures'], report


if __name__ == '__main__':
    main()
