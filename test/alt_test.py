import asyncio
from playwright.async_api import async_playwright
OUT='/home/claude/vp/test/shots'
async def main():
    import os; os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(2)")
        await pg.wait_for_function("S.adim===2 && !mesgul", timeout=300000); await pg.wait_for_timeout(2000)
        await pg.evaluate("manuelAc('rotus')"); await pg.wait_for_selector('#mv canvas', timeout=60000); await pg.wait_for_timeout(1500)
        box=await pg.locator('#mvAlan').bounding_box()
        cx,cy=box['x']+box['width']/2, box['y']+box['height']*0.4
        await pg.mouse.move(cx-100,cy); await pg.mouse.move(cx+60,cy)
        await pg.keyboard.down('Alt'); await pg.wait_for_timeout(200)
        await pg.screenshot(path=f'{OUT}/a1_alt.png',clip={'x':cx-150,'y':cy-120,'width':300,'height':240})
        print('alt-modu', await pg.evaluate("document.querySelector('.mv-imlec').classList.contains('mv-alt-modu')"))
        await pg.mouse.click(cx+60,cy); await pg.keyboard.up('Alt'); await pg.wait_for_timeout(700)
        await pg.mouse.move(cx-40,cy); await pg.mouse.down(); await pg.mouse.move(cx-20,cy+5)
        await pg.screenshot(path=f'{OUT}/a2_boya.png',clip={'x':cx-150,'y':cy-120,'width':300,'height':240})
        await pg.mouse.up()
        print('kaynak',await pg.evaluate("MV.m.kaynak"),'gecmis',await pg.evaluate("MV.m.gecmis.length"),errs)
        await b.close()
asyncio.run(main())
