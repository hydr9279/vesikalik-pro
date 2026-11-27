import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1500)
        await pg.evaluate("yollaEkle(['/tmp/kesik.jpg'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path='test/shots/y0.png'); print(errs)
        await b.close()
asyncio.run(main())
