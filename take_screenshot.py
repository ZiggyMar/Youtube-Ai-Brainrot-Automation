import os
import asyncio
from playwright.async_api import async_playwright

async def main():
    os.makedirs('assets/docs', exist_ok=True)
    # Get absolute path for the layout editor HTML
    html_path = os.path.abspath('tools/layout_editor.html').replace('\\', '/')
    file_url = f"file:///{html_path}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(file_url)
        # Wait for any dynamic content to load
        await asyncio.sleep(2)
        await page.screenshot(path="assets/docs/real_layout_editor_screenshot.png")
        print("Screenshot successfully saved to assets/docs/real_layout_editor_screenshot.png")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
