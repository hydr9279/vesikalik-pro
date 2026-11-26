import asyncio, math
from playwright.async_api import async_playwright
OUT='/home/claude/vp/test/shots'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(2)")
        await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2500)
        await pg.evaluate("manuelAc('rotus')"); await pg.wait_for_selector('#mv canvas', timeout=60000); await pg.wait_for_timeout(1500)
        box=await pg.locator('#mvAlan').bounding_box(); cx,cy=box['x']+box['width']/2, box['y']+box['height']*0.45
        await pg.screenshot(path=f'{OUT}/n1_klon_ust.png')
        await pg.mouse.move(cx,cy); await pg.mouse.click(cx,cy,button='right'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{OUT}/n2_popup.png')
        await pg.fill('.mv-pop input.sayi >> nth=0','90'); await pg.wait_for_timeout(200)
        print('boyut',await pg.evaluate("MV.m.boyut"))
        await pg.mouse.click(cx-300,cy-250); await pg.wait_for_timeout(200); print('popup kapandi', await pg.locator('.mv-pop').count()==0)
        await pg.keyboard.press('j')
        pts=[(cx-60+40*math.cos(a/10), cy+40*math.sin(a/10)*0.8) for a in range(0,66,3)]
        await pg.mouse.move(*pts[0]); await pg.mouse.down()
        for q in pts[1:]: await pg.mouse.move(*q)
        await pg.screenshot(path=f'{OUT}/n3_lasso_ciz.png')
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{OUT}/n4_secim.png')
        await pg.mouse.move(cx-60,cy); await pg.mouse.down(); await pg.mouse.move(cx+90,cy+60,steps=6)
        await pg.screenshot(path=f'{OUT}/n5_surukle.png')
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        print('gecmis',await pg.evaluate("MV.m.gecmis.length"), 'ERR',errs[:5])
        await b.close()
asyncio.run(main())
