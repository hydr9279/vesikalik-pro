import asyncio
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
        n=0
        async def stroke(key, alt=False):
            nonlocal n
            await pg.keyboard.press(key)
            if alt:
                await pg.keyboard.down('Alt'); await pg.mouse.click(cx+70,cy+10); await pg.keyboard.up('Alt')
            await pg.mouse.move(cx-40,cy+20); await pg.mouse.down()
            for i in range(12): await pg.mouse.move(cx-40+i*5,cy+20+i)
            await pg.mouse.up(); await pg.wait_for_timeout(200); n+=1
            print(key,'gecmis',await pg.evaluate("MV.m.gecmis.length"))
        for k,alt in [('h',True),('p',False),('l',False),('b',False),('t',False),('o',False)]: await stroke(k,alt)
        await pg.screenshot(path=f'{OUT}/o1_araclar.png')
        await pg.keyboard.press('Control+z'); print('geri',await pg.evaluate("MV.m.gecmis.length"))
        print('ERR',errs[:5]); await b.close()
asyncio.run(main())
