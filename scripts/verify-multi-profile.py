"""Optional real-browser smoke test using synthetic profiles in temporary storage.

Run from the checkout: .venv/Scripts/python.exe scripts/verify-multi-profile.py
Requires the optional Playwright dependency and a Chromium installation.
"""
import asyncio
from pathlib import Path
import socket
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn
from playwright.async_api import async_playwright
from app.main import create_app


async def main():
    with tempfile.TemporaryDirectory(prefix='careerpulse-browser-') as root:
        app = create_app(data_root=root, testing=True)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', timeout_graceful_shutdown=2))
        serving = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            for _ in range(100):
                if server.started:
                    break
                if serving.done():
                    await serving
                await asyncio.sleep(.05)
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(channel='chrome', headless=True)
                try:
                    page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    await page.goto(f'http://127.0.0.1:{port}/')
                    await page.get_by_label('Display name').fill('Synthetic First')
                    await page.get_by_role('button', name='Create profile').click()
                    await page.wait_for_url('**/profiles/**')
                    first_url = page.url.split('#')[0]
                    await page.get_by_role('dialog').wait_for()
                    await page.get_by_role('button', name='Finish setup later').click()
                    await page.get_by_role('combobox', name='Candidate profile').wait_for()
                    first_id = first_url.split('/profiles/')[1].strip('/')
                    await page.get_by_role('link', name='Manage profiles').click()
                    await page.get_by_label('Display name').fill('Synthetic Second')
                    await page.get_by_role('button', name='Create profile').click()
                    await page.wait_for_url('**/profiles/**')
                    second_url = page.url.split('#')[0]
                    await page.get_by_role('dialog').wait_for()
                    await page.get_by_role('button', name='Finish setup later').click()
                    selector = page.get_by_role('combobox', name='Candidate profile')
                    await selector.select_option(first_id)
                    await page.wait_for_url(first_url + '**')
                    # A second tab stays on its own candidate when the first switches.
                    other = await browser.new_page()
                    await other.goto(second_url)
                    await other.get_by_role('combobox', name='Candidate profile').wait_for()
                    assert await page.get_by_role('combobox', name='Candidate profile').input_value() == first_id
                    assert await other.get_by_role('combobox', name='Candidate profile').input_value() != first_id
                    await page.get_by_role('link', name='Dashboard', exact=True).click()
                    await page.wait_for_timeout(700)
                    assert not errors, errors
                    screenshot = Path(tempfile.gettempdir()) / 'careerpulse-profiles-smoke.png'
                    await page.screenshot(path=str(screenshot), full_page=True)
                    print(f'PASS: UI creation, onboarding, profile navigation, simultaneous tabs, dashboard. Screenshot: {screenshot}')
                finally:
                    await browser.close()
        finally:
            server.should_exit = True
            await serving
            sock.close()


if __name__ == '__main__':
    asyncio.run(main())
