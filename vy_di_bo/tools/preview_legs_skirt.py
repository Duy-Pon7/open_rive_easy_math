"""Render the actual exported files at three walk phases."""
import threading
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from check_walk import decode
from serve_walk import ROOT,server


def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    sheet=Image.new('RGB',(3*600,2*872),'#252525')
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        for row in range(2):
            tab=browser.new_page()
            if row==0:
                tab.route('**/vy_di_bo.riv',lambda route:route.fulfill(
                    body=(ROOT/'verification/before-legs-skirt.riv').read_bytes(),content_type='application/octet-stream'))
            tab.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
            tab.wait_for_function('window.ready || window.failure');assert tab.evaluate('window.failure') is None
            tab.evaluate('document.getElementById("scene").width=982;document.getElementById("scene").height=1734')
            for col,frame in enumerate([0,18,54]):
                im=decode(tab.evaluate('t=>vyWalk.pose(t)',frame/60)).crop((220,860,820,1700))
                sheet.paste(im,(col*600,row*872),im)
                ImageDraw.Draw(sheet).text((col*600+12,row*872+852),f'{"Before" if row==0 else "Fixed"} - frame {frame}',fill='white')
            tab.close()
        browser.close()
    app.shutdown();sheet.save(ROOT/'vy_di_bo_legs_skirt_before_after.png')


if __name__=='__main__':main()
