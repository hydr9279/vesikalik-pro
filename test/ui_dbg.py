import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1440,'height':900})
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(1200)
        await pg.evaluate("S.ayar.model='isnet'; yollaEkle(['/home/claude/ornekler/orijinal/IMG_7924.JPG'])")
        await pg.wait_for_function("S.st && S.st.uygunluk", timeout=120000)
        await pg.evaluate("adimaGit(3)"); await pg.wait_for_function("S.adim===3 && !mesgul", timeout=400000); await pg.wait_for_timeout(1500)
        r=await pg.evaluate("""document.elementsFromPoint(380,210).map(e=>e.tagName+'.'+(e.className.baseVal??e.className)).join(' > ')""")
        print(r)
        await b.close()
asyncio.run(main())
