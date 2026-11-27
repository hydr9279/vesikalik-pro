import asyncio
from playwright.async_api import async_playwright
OUT='test/shots'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/home/claude/ornekler/orijinal/IMG_7923.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("S.ayar.model='isnet'; adimaGit(2)")
        await pg.wait_for_function("S.adim===2 && !mesgul", timeout=500000); await pg.wait_for_timeout(2000)
        # rötuş
        box=await pg.locator(".tuval-alan").bounding_box()
        await pg.screenshot(path=f'{OUT}/u3.png')
        await pg.keyboard.press('l'); await pg.wait_for_timeout(400)
        await pg.mouse.click(box['x']+500,box['y']+300); await pg.wait_for_timeout(300)
        await pg.mouse.click(box['x']+560,box['y']+360); await pg.wait_for_timeout(300)
        await pg.locator('.leke-bekleyen').first.click(button='right'); await pg.wait_for_timeout(400)
        await pg.screenshot(path=f'{OUT}/u4.png')
        await pg.evaluate("document.querySelector('#laB').value=30;document.querySelector('#laB').dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#laY').value=60;document.querySelector('#laY').dispatchEvent(new Event('input',{bubbles:true}))")
        await pg.click('#laTamam'); await pg.wait_for_timeout(200)
        await pg.click('#lUygula'); await pg.wait_for_timeout(45000); print("dbg", await pg.evaluate("[mesgul, JSON.stringify(S.st.gecmis), S.bLeke[S.cur]&&S.bLeke[S.cur].length]")); await pg.wait_for_function("!mesgul", timeout=240000); await pg.wait_for_timeout(2000)
        print('spots', await pg.evaluate("JSON.stringify(S.st.lekeler)"), await pg.inner_text('.gecmis-bilgi'))
        await pg.screenshot(path=f'{OUT}/u5.png')
        await pg.locator('.leke-isaret').last.click(button='right'); await pg.wait_for_function("!mesgul", timeout=240000); await pg.wait_for_timeout(2000)
        print('silindi', await pg.evaluate("S.st.lekeler.length"), await pg.inner_text('.gecmis-bilgi'))
        await pg.keyboard.press('o' if False else 'v'); await pg.wait_for_timeout(300)
        print('rArac', await pg.evaluate("S.rArac"), errs)
        await pg.screenshot(path=f'{OUT}/u6.png')
        await b.close()
asyncio.run(main())
