"""Check the exported neck/collar join, including the former seam spike."""
import json
import threading

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from check_huy import decode
from serve_huy import ROOT, server


def main():
    app = server()
    threading.Thread(target=app.serve_forever, daemon=True).start()
    qa = ROOT / 'verification'
    records = []
    poses = [0, 3.7, 11.9]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge')
        page = browser.new_page()
        page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        page.wait_for_function('window.ready || window.failure')
        assert page.evaluate('window.failure') is None
        for talking, count in [(False, 270), (True, 24)]:
            page.evaluate('(talking)=>{huy.fresh();huy.set(2,talking);}', talking)
            for i in range(count):
                im = decode(page.evaluate('()=>{huy.advance(1/15);return huy.draw();}'))
                a = np.array(im)
                # Entire interior collar region, including the old skin tip
                # and both neck/shirt boundaries; none may expose background.
                alpha = a[264:298, 105:162, 3]
                records.append(dict(talking=talking, frame=i, min_alpha=int(alpha.min()),
                                    underfilled_pixels=int((alpha < 250).sum())))
        after = []
        for t in poses:
            im = decode(page.evaluate('(t)=>{huy.fresh();huy.advance(t);return huy.draw();}', t))
            after.append(im)
        before_page = browser.new_page()
        before_page.route('**/huy_goc_3_4_noi_speaking_vi.riv',
                          lambda route: route.fulfill(path=str(qa/'before_neck_fix/huy_goc_3_4_noi_speaking_vi.riv'),
                                                     content_type='application/octet-stream'))
        before_page.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
        before_page.wait_for_function('window.ready || window.failure')
        before = [decode(before_page.evaluate('(t)=>{huy.fresh();huy.advance(t);return huy.draw();}', t)) for t in poses]
        browser.close()
    app.shutdown()
    scale = 4
    box = (85, 225, 181, 305)
    cell_w, cell_h = 384, 350
    sheet = Image.new('RGB', (3*cell_w, 2*cell_h), '#e6e9ed')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
    for row, frames in enumerate([before, after]):
        for col, (im, t) in enumerate(zip(frames, poses)):
            bg = Image.new('RGBA', im.size, '#e6e9ed')
            bg.alpha_composite(im)
            crop = bg.crop(box).convert('RGB').resize((96*scale, 80*scale), Image.Resampling.LANCZOS)
            x, y = col*cell_w, row*cell_h
            sheet.paste(crop, (x, y+30))
            draw.text((x+10, y+3), f'{"Before" if row == 0 else "After"} - {t:g}s', fill='#18324b', font=font)
    sheet.save(qa/'neck_before_after.png')
    report = dict(frames=len(records), idle_frames=270, talking_frames=24,
                  max_underfilled_collar_pixels=max(r['underfilled_pixels'] for r in records),
                  min_collar_alpha=min(r['min_alpha'] for r in records),
                  failures=[r for r in records if r['underfilled_pixels']])
    (qa/'neck-runtime-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2), flush=True)
    assert not report['failures'], report


if __name__ == '__main__':
    main()
