"""Exercise native numeric color selection through the actual state machine."""
from pathlib import Path
from collections import Counter
import base64
import io
import json

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent
palettes=json.loads((ROOT/'verification/balloon-palettes.json').read_text())

def rgb(value):
    return tuple(bytes.fromhex(value.lstrip('#')))

sheet=Image.new('RGB',(407*3,570*3),'#eae8e2')
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=r'C:\Users\Duy\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe')
    page=browser.new_page(viewport={'width':1100,'height':1150})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8769/mascot/preview.html');page.wait_for_function('window.ready')
    page.evaluate('r.on(rive.EventType.StateChange,e=>{window.colorStates=(window.colorStates||[]).concat(e.data)})')
    def capture():
        data=page.locator('canvas').evaluate('c=>c.toDataURL()')
        return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
    for row,(name,palette) in enumerate(palettes.items()):
        page.locator('#run').click()
        page.locator(f'[data-color="{row}"]').click();page.wait_for_timeout(120)
        assert page.evaluate('balloonColor.value')==row
        snapshots=[capture()]
        page.locator('#fall').click();page.wait_for_timeout(400);snapshots.append(capture())
        page.wait_for_timeout(1200);snapshots.append(capture())
        for column,(phase,im) in enumerate(zip(['Held','Falling','Splash'],snapshots)):
            colors=Counter(im.convert('RGB').getdata())
            target=palette['#4299fd' if phase!='Splash' else '#66b8fd']
            assert colors[rgb(target)]>100,(name,phase,target)
            if row:
                assert sum(colors[rgb(blue)] for blue in palettes['Blue'].values())==0,(name,phase,'blue residue')
            checks.append({'color':row,'palette':name,'phase':phase,'exact_color_pixels':colors[rgb(target)]})
            small=im.resize((407,543),Image.Resampling.LANCZOS);bg=Image.new('RGB',small.size,'white');bg.paste(small,mask=small.getchannel('A'))
            x,y=column*407,row*570;sheet.paste(bg,(x,y));ImageDraw.Draw(sheet).text((x+12,y+548),f'{row} - {name} | {phase}',fill='#333')
    # Changing colors after impact must recolor the puddle immediately without replaying Fall.
    for value,name in [(0,'Blue'),(1,'Yellow'),(2,'Pink')]:
        page.locator(f'[data-color="{value}"]').click();page.wait_for_timeout(100)
        count=Counter(capture().convert('RGB').getdata())
        assert count[rgb(palettes[name]['#66b8fd'])]>100
        assert page.evaluate('falling.value')
    page.locator('#run').click();page.wait_for_timeout(100)
    assert page.evaluate('balloonColor.value')==2
    assert not page.evaluate('falling.value')
    # A paused timeline can be inspected in the chosen color.
    page.locator('#fall').click();page.wait_for_timeout(250);page.locator('#scrub').fill('0.7');page.wait_for_timeout(80)
    assert page.locator('[data-color="2"]').get_attribute('aria-pressed')=='true'
    page.locator('[data-color="1"]').click();page.wait_for_timeout(150)
    assert page.evaluate('balloonColor.value')==1
    page.locator('[data-color="0"]').click();page.locator('#run').click()
    assert not errors,errors
    (ROOT/'verification/color-runtime-checks.json').write_text(json.dumps({'checks':checks,'live_recolor_after_impact':True,'persists_after_reset':True,'errors':errors},indent=2))
    sheet.save(ROOT/'balloon_color_options.png')
    page.screenshot(path=str(ROOT/'preview.png'))
    print('Verified all 3 palettes during held, falling and splash; live recolor; reset; no runtime errors.')
    browser.close()
