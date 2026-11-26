import asyncio
from playwright.async_api import async_playwright
OUT='/home/claude/vp/test/shots'
async def main():
    import os; os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e))); pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
        pg.on('dialog',lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(1)")
        await pg.wait_for_function("S.adim===1 && !mesgul", timeout=300000); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=f'{OUT}/m0_arka.png')
        # dekupe
        await pg.evaluate("manuelAc('dekupe')"); await pg.wait_for_selector('#mv canvas', timeout=60000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=f'{OUT}/m1_dekupe.png')
        box=await pg.locator('#mvAlan').bounding_box()
        cx,cy=box['x']+box['width']/2, box['y']+box['height']*0.3
        await pg.mouse.move(cx-80,cy); await pg.mouse.down()
        for i in range(30): await pg.mouse.move(cx-80+i*6,cy+i*2)
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        await pg.screenshot(path=f'{OUT}/m2_dekupe_stroke.png')
        print('gecmis', await pg.evaluate("MV.m.gecmis.length"))
        await pg.click('#mvUygula'); await pg.wait_for_function("!MV.acik && !mesgul", timeout=60000); await pg.wait_for_timeout(1500)
        print('manuel_var', await pg.evaluate("S.st.manuel_var"))
        await pg.evaluate("adimaGit(2)"); await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=f'{OUT}/m3_rotus.png')
        await pg.evaluate("manuelAc('rotus')"); await pg.wait_for_selector('#mv canvas', timeout=60000); await pg.wait_for_timeout(1500)
        box=await pg.locator('#mvAlan').bounding_box()
        cx,cy=box['x']+box['width']/2, box['y']+box['height']*0.4
        # klon: alt+click kaynak
        await pg.keyboard.down('Alt'); await pg.mouse.click(cx+60,cy); await pg.keyboard.up('Alt')
        await pg.mouse.move(cx-40,cy); await pg.mouse.down()
        for i in range(20): await pg.mouse.move(cx-40+i*3,cy+i)
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        # yama
        await pg.keyboard.press('j')
        await pg.mouse.move(cx-150,cy+100); await pg.mouse.down()
        for a in range(0,360,30):
            import math; await pg.mouse.move(cx-150+30*math.cos(math.radians(a)), cy+100+30*math.sin(math.radians(a)))
        await pg.mouse.up(); await pg.mouse.move(cx-150,cy+100); await pg.mouse.down(); await pg.mouse.move(cx-100,cy+130,steps=5); await pg.mouse.up()
        await pg.keyboard.press('q'); await pg.mouse.click(cx+100,cy+50)
        await pg.keyboard.press('w'); await pg.mouse.move(cx,cy+60); await pg.mouse.down(); await pg.mouse.move(cx+40,cy+70,steps=8); await pg.mouse.up()
        await pg.wait_for_timeout(300)
        print('gecmis', await pg.evaluate("MV.m.gecmis.length"))
        await pg.screenshot(path=f'{OUT}/m4_rotus_mv.png')
        await pg.keyboard.press('Control+z'); print('geri', await pg.evaluate("MV.m.gecmis.length"))
        await pg.click('#mvUygula'); await pg.wait_for_function("!MV.acik && !mesgul", timeout=120000); await pg.wait_for_timeout(1500)
        print('manuel_var', await pg.evaluate("S.st.manuel_var"))
        await pg.screenshot(path=f'{OUT}/m5_rotus_son.png')
        print('ERR',errs[:10])
        await b.close()
asyncio.run(main())
