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
                    await page.get_by_label('Display name').fill('Cancelled draft')
                    await page.get_by_role('button', name='Cancel', exact=True).click()
                    assert await page.get_by_label('Display name').input_value() == ''
                    await page.get_by_label('Display name').fill('Synthetic First')
                    await page.get_by_role('button', name='Create profile').click()
                    await page.get_by_role('link', name='Set up profile').wait_for()
                    assert page.url == f'http://127.0.0.1:{port}/'
                    await page.get_by_role('link', name='Set up profile').click()
                    await page.wait_for_url('**/profiles/**')
                    first_url = page.url.split('#')[0]
                    await page.get_by_role('dialog').wait_for()
                    await page.get_by_role('link', name='Back to Manage profiles').click()
                    await page.get_by_role('link', name='Synthetic First', exact=True).click()
                    await page.get_by_role('dialog').wait_for()
                    await page.get_by_role('button', name='Finish setup later').click()
                    await page.get_by_role('combobox', name='Candidate profile').wait_for()
                    first_id = first_url.split('/profiles/')[1].strip('/')
                    await page.get_by_role('link', name='Manage profiles').click()
                    await page.get_by_label('Display name').fill('Synthetic Second')
                    await page.get_by_role('button', name='Create profile').click()
                    await page.get_by_role('link', name='Set up profile').click()
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
                    # Exercise a real status save and browser refresh in temporary storage.
                    base = f'http://127.0.0.1:{port}/api/candidates/{first_id}'
                    added = await page.request.post(base + '/jobs/save-external', data={
                        'title': 'Synthetic pipeline job', 'company': 'Example',
                        'url': 'https://example.invalid/pipeline', 'initial_status': 'applied'})
                    assert added.ok
                    await page.get_by_role('link', name='Pipeline', exact=True).click()
                    applied_card = page.locator('.pipeline-cards[data-status="applied"] .pipeline-card')
                    await applied_card.drag_to(page.locator('.pipeline-cards[data-status="rejected"]'))
                    await page.locator('.pipeline-cards[data-status="rejected"] .pipeline-card').wait_for()
                    await page.reload()
                    await page.locator('.pipeline-cards[data-status="rejected"] .pipeline-card').wait_for()
                    assert await page.locator('.pipeline-cards[data-status="applied"] .pipeline-card').count() == 0
                    await page.get_by_role('link', name='Dashboard', exact=True).click()
                    await page.wait_for_timeout(700)
                    assert not errors, errors
                    screenshot = Path(tempfile.gettempdir()) / 'careerpulse-profiles-smoke.png'
                    await page.screenshot(path=str(screenshot), full_page=True)
                    await other.close()
                    await page.goto(f'http://127.0.0.1:{port}/')
                    page.once('dialog', lambda dialog: dialog.accept('Renamed First'))
                    await page.get_by_role('button', name='Rename: Synthetic First', exact=True).click()
                    await page.get_by_role('link', name='Renamed First', exact=True).wait_for()
                    await page.reload()
                    await page.get_by_role('link', name='Renamed First', exact=True).wait_for()
                    page.once('dialog', lambda dialog: dialog.dismiss())
                    await page.get_by_role('button', name='Delete profile: Renamed First', exact=True).click()
                    assert await page.get_by_role('link', name='Renamed First', exact=True).count() == 1
                    page.once('dialog', lambda dialog: dialog.accept('Renamed First'))
                    await page.get_by_role('button', name='Delete profile: Renamed First', exact=True).click()
                    await page.get_by_text('Profile deleted.', exact=True).wait_for()
                    assert await page.get_by_role('link', name='Renamed First', exact=True).count() == 0
                    assert await page.get_by_role('link', name='Synthetic Second', exact=True).count() == 1
                    assert not errors, errors
                    await page.screenshot(path=str(screenshot), full_page=True)
                    print(f'PASS: profile creation, rename persistence, delete/cancel, isolation, onboarding, pipeline persistence, dashboard. Screenshot: {screenshot}')
                finally:
                    await browser.close()
        finally:
            server.should_exit = True
            await serving
            sock.close()


if __name__ == '__main__':
    asyncio.run(main())
