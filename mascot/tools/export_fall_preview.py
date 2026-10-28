from pathlib import Path
import base64
import io
import json

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=r'C:\Users\Duy\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe')
    page = browser.new_page(viewport={'width': 1000, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8769/mascot/preview.html')
    page.wait_for_function('window.ready === true')
    page.evaluate('r.on(rive.EventType.StateChange,e=>{window.stateLog=(window.stateLog||[]).concat(e.data)})')
    # Exercise both transitions and replay through the actual data-bound state machine.
    page.locator('#fall').click(); page.wait_for_timeout(1600)
    assert page.evaluate('falling.value')
    assert 'Fall' in page.evaluate('window.stateLog')
    page.locator('#fall').click(); page.wait_for_timeout(300)
    assert page.evaluate('window.stateLog.filter(x=>x==="Fall").length') >= 2
    page.locator('#toggle').click(); assert not page.evaluate('playing')
    page.locator('#toggle').click(); assert page.evaluate('playing')
    page.evaluate('window.stateLog=[]')
    page.locator('#run').click(); page.wait_for_timeout(200)
    assert not page.evaluate('falling.value')
    assert 'Run' in page.evaluate('window.stateLog')
    test_results = {'states':page.evaluate('window.stateLog'),'replay':True,'reset':True,'pause_resume':True,'errors':errors}
    project = json.loads((ROOT/'openrive-project.json').read_text(encoding='utf8'))
    speeds = {a['props']['name']: a['props'].get('speed',1) for a in project['artboards'][0]['animations']}
    frames=[]
    durations=[]
    elapsed_ms=0
    for animation, count in [('Run',15),('Fall',39)]:
        page.evaluate('(name)=>{r.stop();r.play(name);r.pause()}',animation)
        for i in range(count):
            t=min(i*.04,1.5)
            page.evaluate('([name,t])=>r.scrub(name,t)',[animation,t/speeds[animation]]);page.wait_for_timeout(22)
            data=page.locator('canvas').evaluate('c=>c.toDataURL("image/png")')
            im=Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA').resize((407,543),Image.Resampling.LANCZOS)
            bg=Image.new('RGB',im.size,'white');bg.paste(im,mask=im.getchannel('A'));frames.append(bg)
            previous = round(elapsed_ms/10)*10
            elapsed_ms += 40/speeds[animation]
            durations.append(max(10,round(elapsed_ms/10)*10-previous))
    durations[-1]=850
    frames[0].save(ROOT/'mascot_run_fall.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
    page.screenshot(path=str(ROOT/'preview.png'))
    test_results['transparent_corner'] = im.getpixel((0,0))[3] == 0
    assert test_results['transparent_corner']
    assert not errors
    # Resume the real controller for a final screenshot showing the product controls.
    page.locator('#run').click();page.locator('#fall').click();page.wait_for_timeout(1550)
    page.screenshot(path=str(ROOT/'preview.png'))
    (ROOT/'fall-runtime-checks.json').write_text(json.dumps(test_results,indent=2))
    print(json.dumps(test_results))
    browser.close()
