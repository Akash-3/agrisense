import asyncio
from playwright.async_api import async_playwright

VIEWPORTS = [
    {"name": "Mobile Small", "width": 360, "height": 800},
    {"name": "Mobile Medium", "width": 390, "height": 844},
    {"name": "Tablet", "width": 768, "height": 1024},
    {"name": "Desktop", "width": 1440, "height": 900}
]

async def run_strict_viewport_test(p, vp):
    print(f"\n--- TESTING VIEWPORT (STRICT PHYSICAL MOUSE CLICK): {vp['name']} ({vp['width']}x{vp['height']}) ---")
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
    page = await context.new_page()

    console_errors = []
    failed_requests = []
    
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("response", lambda res: failed_requests.append(f"{res.status} {res.url}") if res.status >= 400 else None)

    # 1. Load actual page
    await page.goto("http://127.0.0.1:8000")
    await page.wait_for_selector("#loginIdInput")

    # 2. Login through real UI
    await page.fill("#loginIdInput", "qa_farmer@agrisense.io")
    await page.fill("#loginPassInput", "Password123!")
    await page.click("button:has-text('Sign In to Account')")
    await page.wait_for_selector("#mainAppScreen:not(.hidden)", timeout=10000)

    # 3. Handle mobile sidebar drawer toggle on small viewports (< 1024px)
    if vp["width"] < 1024:
        menu_btn = page.locator("#mobileMenuBtn")
        await menu_btn.click()
        await page.wait_for_selector("#sidebar:not(.-translate-x-full)", timeout=5000)
        # Wait 350ms for CSS transition duration-300 to settle
        await page.wait_for_timeout(350)

    # 4. Get center coordinates of AI Assistant sidebar button
    btn_info = await page.evaluate("""() => {
        const btn = document.querySelector('#sidebar button[data-view="chatbot"]');
        if (!btn) return null;
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const topEl = document.elementFromPoint(cx, cy);
        return {
            cx: cx,
            cy: cy,
            topTagName: topEl ? topEl.tagName : null,
            topText: topEl ? topEl.innerText : null,
            isButtonOrChild: topEl ? (topEl === btn || btn.contains(topEl)) : false
        };
    }""")

    assert btn_info is not None, f"AI Assistant button missing in DOM on {vp['name']}"
    assert btn_info["isButtonOrChild"], f"elementFromPoint({btn_info['cx']}, {btn_info['cy']}) returned {btn_info['topTagName']} ('{btn_info['topText']}'), expected AI Assistant button!"

    # 5. Move mouse to center coordinates & click (STRICT PHYSICAL MOUSE CLICKS ONLY)
    await page.mouse.move(btn_info["cx"], btn_info["cy"])
    await page.mouse.click(btn_info["cx"], btn_info["cy"])

    # 6. Wait for #agri-chat-window to become visible
    chat_win = page.locator("#agri-chat-window")
    await chat_win.wait_for(state="visible", timeout=5000)

    # 7. Verify chatbot input and close button are visible
    chat_input = page.locator("#agri-chat-input")
    assert await chat_input.is_visible(), f"Chat input field is not visible on {vp['name']}!"

    close_btn = page.locator("#agri-chat-window .agri-chat-header button:has-text('✖')")
    assert await close_btn.is_visible(), f"Chat header close button is not visible on {vp['name']}!"

    # 8. Type a real message and click Send
    test_msg = f"How to protect paddy crops from stem borer in {vp['name']}?"
    await chat_input.fill(test_msg)
    send_btn = page.locator("#agri-chat-window .agri-chat-send-btn")
    await send_btn.click()

    # 9. Verify user message appears in chat
    user_msg_loc = page.locator(f".chat-msg.user-msg:has-text('{test_msg}')")
    await user_msg_loc.wait_for(state="visible", timeout=5000)

    # 10. Verify actual AI response appears (not stuck on typing indicator)
    bot_msg_loc = page.locator(".chat-msg.bot-msg:not(:has-text('Thinking'))").nth(1)
    await bot_msg_loc.wait_for(state="visible", timeout=15000)

    bot_text = await bot_msg_loc.text_content()
    safe_bot_text = bot_text.encode('ascii', errors='replace').decode('ascii')
    print(f"Received AI Bot Response: {safe_bot_text[:120]}...")

    assert len(console_errors) == 0, f"Console errors detected on {vp['name']}: {console_errors}"
    assert len(failed_requests) == 0, f"Failed network requests detected on {vp['name']}: {failed_requests}"

    print(f"PASSED STRICT PHYSICAL CLICK TEST: {vp['name']} ({vp['width']}x{vp['height']})")
    await browser.close()

async def main():
    async with async_playwright() as p:
        for vp in VIEWPORTS:
            await run_strict_viewport_test(p, vp)

if __name__ == "__main__":
    asyncio.run(main())
