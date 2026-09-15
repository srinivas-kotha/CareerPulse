"""Browser regression for discovery controls, plus an optional read-only live check.

Run from checkout with .venv/Scripts/python.exe scripts/verify-discovery-ui.py.
Use --base-url http://127.0.0.1:8085 --candidate UUID for read-only live verification.
Screenshots are written outside Git to the operating system's temporary directory.
"""
import argparse
import asyncio
from pathlib import Path
import socket
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import uvicorn
from playwright.async_api import async_playwright

from app.main import create_app


async def browser_check(base, candidate, synthetic=False):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="chrome", headless=True)
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 1100})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            profile = f"{base}/profiles/{candidate}/"
            await page.goto(profile + '#/stats')
            await page.locator('#discovery-health').wait_for()
            later = page.get_by_role('button', name='Finish setup later')
            if await later.count():
                await later.click()
            if synthetic:
                async with page.expect_response(lambda r: r.url.endswith('/discovery/audit') and r.request.method == 'POST'):
                    await page.get_by_role('button', name='Check listing quality and duplicates').click()
                await page.get_by_text('1 listing quality reviews', exact=False).wait_for()
            await page.reload()
            await page.locator('#discovery-health').wait_for()
            if await later.count():
                await later.click()
            assert await page.get_by_role('button', name='Check availability of 10 listings').count() == 1
            if synthetic:
                await page.goto(profile + '#/')
                await page.locator('#filter-score').select_option('')
                await page.get_by_text('Backend Engineer', exact=True).first.wait_for()
                assert await page.get_by_text('London, UK', exact=True).count() == 0
                await page.locator('#filter-include-review').check()
                await page.get_by_text('London, UK', exact=True).first.wait_for()
                await page.goto(profile + '#/job/2')
                async with page.expect_response(lambda r: r.url.endswith('/jobs/2/availability') and r.request.method == 'POST'):
                    await page.get_by_role('button', name='Check listing availability').click()
                await page.get_by_text('Availability: closed', exact=False).wait_for()
                await page.reload()
                await page.get_by_text('Availability: closed', exact=False).wait_for()
                assert await page.get_by_text('Quality: review.', exact=False).count() == 1
                await page.goto(profile + '#/stats')
                await page.locator('#discovery-health').wait_for()
                await page.get_by_text('1 confirmed closed', exact=False).wait_for()
            await page.locator('#discovery-health').scroll_into_view_if_needed()
            screenshot = Path(tempfile.gettempdir()) / ('careerpulse-discovery-synthetic.png' if synthetic else 'careerpulse-discovery-live.png')
            await page.screenshot(path=str(screenshot))
            assert not errors, errors
            print(f"PASS: {'synthetic controls, filters and persisted availability' if synthetic else 'live dashboard and reload'}; no JavaScript errors. Screenshot: {screenshot}")
        except Exception:
            print('Browser failure:', page.url, errors, (await page.locator('body').inner_text())[:700])
            await page.screenshot(path=str(Path(tempfile.gettempdir()) / 'careerpulse-discovery-failure.png'))
            raise
        finally:
            await browser.close()


async def main(args):
    if args.base_url:
        if not args.candidate:
            raise ValueError('--candidate is required for live verification')
        await browser_check(args.base_url.rstrip('/'), args.candidate)
        return
    with tempfile.TemporaryDirectory(prefix='careerpulse-discovery-ui-') as root:
        app = create_app(data_root=root, testing=True)
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        base = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', timeout_graceful_shutdown=2))
        serving = asyncio.create_task(server.serve(sockets=[sock]))
        try:
            while not server.started:
                if serving.done():
                    await serving
                await asyncio.sleep(.05)
            async with httpx.AsyncClient(base_url=base) as client:
                response = await client.post('/api/candidates', json={'display_name': 'Synthetic Discovery'})
                response.raise_for_status()
                candidate = response.json()['candidate_id']
            child = await app.state.get_child(candidate)
            await child.state.db.save_company('Example', description='Synthetic company for an offline UI test')
            for index, title in enumerate(('Backend Engineer', 'London, UK'), 1):
                await child.state.db.insert_job(title=title, company='Example', location='Remote',
                    description='Build Python APIs and maintain distributed services. ' * 6,
                    url=f'https://example.invalid/{index}', salary_min=None, salary_max=None,
                    posted_date=None, application_method='url', contact_email=None)
                await child.state.db.set_job_location_region(index, 'US')
            import app.discovery
            original = app.discovery.check_availability
            async def closed(job):
                return {'status': 'closed', 'reason': 'Synthetic HTTP 410', 'checked_at': '2026-09-14T00:00:00+00:00'}
            app.discovery.check_availability = closed
            try:
                await browser_check(base, candidate, synthetic=True)
                assert (await child.state.db.get_job(2))['availability_status'] == 'closed'
            finally:
                app.discovery.check_availability = original
        finally:
            server.should_exit = True
            await serving


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url')
    parser.add_argument('--candidate')
    asyncio.run(main(parser.parse_args()))
