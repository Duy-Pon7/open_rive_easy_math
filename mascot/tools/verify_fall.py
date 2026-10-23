from pathlib import Path
import base64
import io
import json

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=r'C:\Users\Duy\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe')
    page = browser.new_page(viewport={'width': 1000, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8769/mascot/preview.html')
    page.wait_for_function('window.ready === true')
    states = []
    page.evaluate('r.on(rive.EventType.StateChange, e => { window.stateLog = (window.stateLog || []).concat(e.data); })')
    page.locator('#fall').click()
    page.wait_for_timeout(1650)
    print('After fall:', page.evaluate('({stateLog:window.stateLog, isFalling:falling.value})'))
    page.locator('#run').click()
    page.wait_for_timeout(180)
    print('After reset:', page.evaluate('({stateLog:window.stateLog,isFalling:falling.value})'))
    page.evaluate('r.stop();r.play("Fall");r.pause()')
    def frame(t):
        page.evaluate('(t)=>r.scrub("Fall",t)', t)
        page.wait_for_timeout(30)
        data = page.locator('canvas').evaluate('c=>c.toDataURL("image/png")')
        return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
    samples = [0, .16, .3, .5, .7, .8, 1.1, 1.5]
    sheet = Image.new('RGB', (407*4, 570*2), '#eae8e2')
    for i, t in enumerate(samples):
        im = frame(t).resize((407, 543), Image.Resampling.LANCZOS)
        white = Image.new('RGB', im.size, 'white');white.paste(im, mask=im.getchannel('A'))
        sheet.paste(white, (i % 4*407, i // 4*570))
        ImageDraw.Draw(sheet).text((i % 4*407+12, i // 4*570+548), f'Fall {t:.2f}s', fill='#333')
    sheet.save(ROOT/'fall-contact-sheet.png')
    frame(1.5).resize((543,724),Image.Resampling.LANCZOS).save(ROOT/'fall-final.png')
    print('Runtime errors:', errors)
    browser.close()
