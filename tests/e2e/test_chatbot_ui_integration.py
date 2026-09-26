import asyncio
import pytest
from playwright.async_api import async_playwright

VIEWPORTS = [
    {"name": "Mobile Small", "width": 360, "height": 800},
    {"name": "Mobile Medium", "width": 390, "height": 844},
    {"name": "Tablet", "width": 768, "height": 1024},
    {"name": "Desktop", "width": 1440, "height": 900}
]

async def run_viewport_test(p, vp):
    print(f"\n--- TESTING VIEWPORT: {vp['name']} ({vp['width']}x{vp['height']}) ---")
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
    page = await context.new_page()

    console_errors = []
    failed_requests = []
    
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("response", lambda res: failed_requests.append(f"{res.status} {res.url}") if res.status >= 400 else None)

    # 1. Navigate to page
    await page.goto("http://127.0.0.1:8000")
    await page.wait_for_selector("#loginIdInput")

    # 2. Login via UI
    await page.fill("#loginIdInput", "qa_farmer@agrisense.io")
    await page.fill("#loginPassInput", "Password123!")
    await page.click("button:has-text('Sign In to Account')")
    await page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)

    # 3. Locate and click AI Assistant button in visible sidebar
    # If on mobile/tablet (width < 1024), open mobile menu first
    if vp["width"] < 1024:
        menu_btn = page.locator("#mobileMenuBtn")
        await menu_btn.click()
        await page.wait_for_selector("#sidebar:not(.-translate-x-full)", timeout=5000)

    ai_btn = page.locator("#sidebar button[data-view='chatbot']")
    await ai_btn.wait_for(state="visible", timeout=5000)
    
    # Real mouse click
    await ai_btn.click()

    # 4. Verify chatbot window, input, and close button become visible
    chat_win = page.locator("#agri-chat-window")
    await chat_win.wait_for(state="visible", timeout=5000)
    
    chat_input = page.locator("#agri-chat-input")
    assert await chat_input.is_visible(), "Chat input field is not visible!"

    close_btn = page.locator("#agri-chat-window .agri-chat-header button:has-text('✖')")
    assert await close_btn.is_visible(), "Chat close button is not visible!"

    # 5. Send actual test message through UI
    test_msg = f"Hello from {vp['name']} test!"
    await chat_input.fill(test_msg)
    send_btn = page.locator("#agri-chat-window .agri-chat-send-btn")
    await send_btn.click()

    # 6. Verify user message and bot response appear
    user_msg_loc = page.locator(f".chat-msg.user-msg:has-text('{test_msg}')")
    await user_msg_loc.wait_for(state="visible", timeout=5000)

    bot_msg_loc = page.locator(".chat-msg.bot-msg:not(:has-text('Thinking'))").nth(1)
    await bot_msg_loc.wait_for(state="visible", timeout=15000)
    
    bot_text = await bot_msg_loc.text_content()
    safe_bot_text = bot_text.encode('ascii', errors='replace').decode('ascii')
    print(f"Received bot response: {safe_bot_text[:100]}...")

    print(f"Console errors: {len(console_errors)}")
    print(f"Failed requests: {len(failed_requests)}")

    assert len(console_errors) == 0, f"Console errors detected: {console_errors}"
    assert len(failed_requests) == 0, f"Failed network requests detected: {failed_requests}"
    print(f"PASSED: {vp['name']} ({vp['width']}x{vp['height']})")

    await browser.close()

async def main():
    async with async_playwright() as p:
        for vp in VIEWPORTS:
            await run_viewport_test(p, vp)

if __name__ == "__main__":
    asyncio.run(main())
