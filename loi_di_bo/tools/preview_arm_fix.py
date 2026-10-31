"""Render the actual exported files at four arm-swing phases."""
import threading
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from check_walk import decode
from serve_walk import ROOT,server


def main():
    app=server();threading.Thread(target=app.serve_forever,daemon=True).start()
    sheet=Image.new('RGB',(4*340,2*552),'#252525')
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge')
        for row in range(2):
            tab=browser.new_page()
            if row==0:
                tab.route('**/loi_di_bo.riv',lambda route:route.fulfill(
                    body=(ROOT/'verification/before-left-arm.riv').read_bytes(),content_type='application/octet-stream'))
            tab.goto(f'http://127.0.0.1:{app.server_port}/preview.html')
            tab.wait_for_function('window.ready || window.failure');assert tab.evaluate('window.failure') is None
            tab.evaluate('document.getElementById("scene").width=752;document.getElementById("scene").height=1732')
            for col,frame in enumerate([0,18,36,54]):
                im=decode(tab.evaluate('t=>loiWalk.pose(t)',frame/60)).crop((70,820,410,1340))
                sheet.paste(im,(col*340,row*552),im)
                ImageDraw.Draw(sheet).text((col*340+12,row*552+532),f'{"Before" if row==0 else "Fixed"} - frame {frame}',fill='white')
            tab.close()
        browser.close()
    app.shutdown();sheet.save(ROOT/'loi_di_bo_arm_before_after.png')


if __name__=='__main__':main()
