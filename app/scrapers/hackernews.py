import asyncio
import logging
import time
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, JobListing

logger = logging.getLogger(__name__)

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def parse_hiring_header(text: str) -> dict | None:
    """Read role/location by content, never by a fixed pipe position."""
    from app.discovery import ROLE
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all(["p", "br"]):
        tag.insert_before("\n")
    lines = [line.strip() for line in soup.get_text(" ").splitlines() if line.strip()]
    if not lines:
        return None
    header = lines[0]
    # Older stored descriptions split inline links across lines.
    for line in lines[1:5]:
        if header.count("|") >= 2 and ROLE.search(header):
            break
        if len(header) + len(line) > 600:
            break
        header += " " + line
    parts = [p.strip() for p in header.split("|") if p.strip()]
    if len(parts) < 2:
        return None
    roles = [p for p in parts[1:] if ROLE.search(p) and len(p) <= 180 and not p.startswith("http")]
    if not roles:
        return None
    company = parts[0]
    locations = [p for p in parts[1:] if p not in roles and not p.startswith("http")
                 and not re.search(r"\$|salary|full.time|part.time|equity|visa|sponsor", p, re.I)]
    return {"company": company, "title": roles[0], "location": "; ".join(locations)[:240]}


class HackerNewsScraper(BaseScraper):
    source_name = "hackernews"

    SCRAPE_TIMEOUT = 300  # 5 minutes
    COMMENT_CONCURRENCY = 5

    async def scrape(self) -> list[JobListing]:
        try:
            return await asyncio.wait_for(self._scrape_inner(), timeout=self.SCRAPE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f"HN scraper timed out after {self.SCRAPE_TIMEOUT}s, returning {len(self._partial_results)} partial results")
            return self._partial_results

    async def _scrape_inner(self) -> list[JobListing]:
        self._partial_results = []
        one_month_ago = int(time.time()) - 60 * 60 * 24 * 35

        async with self.get_client() as client:
            try:
                resp = await self.rate_limited_get(
                    client, ALGOLIA_SEARCH_URL,
                    params={
                        "query": "who is hiring",
                        "tags": "story,ask_hn",
                        "numericFilters": f"created_at_i>{one_month_ago}",
                    },
                )
                resp.raise_for_status()
                search_data = resp.json()
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                logger.error(f"HN search failed: {e}")
                return []

            hits = search_data.get("hits", [])
            if not hits:
                return []

            thread_id = hits[0]["objectID"]
            logger.info(f"HN: found hiring thread {thread_id}")

            try:
                resp = await self.rate_limited_get(client, HN_ITEM_URL.format(id=thread_id))
                resp.raise_for_status()
                thread_data = resp.json()
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                logger.error(f"HN thread fetch failed: {e}")
                return []

            kids = thread_data.get("kids", [])[:100]
            logger.info(f"HN: fetching {len(kids)} comments concurrently")

            sem = asyncio.Semaphore(self.COMMENT_CONCURRENCY)
            fetched_count = 0

            async def fetch_comment(kid_id: int) -> JobListing | None:
                nonlocal fetched_count
                async with sem:
                    try:
                        resp = await self.rate_limited_get(client, HN_ITEM_URL.format(id=kid_id))
                        resp.raise_for_status()
                        comment = resp.json()
                    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
                        logger.warning(f"HN comment {kid_id} fetch failed: {e}")
                        return None

                    fetched_count += 1
                    if fetched_count % 25 == 0:
                        logger.info(f"HN: fetched {fetched_count}/{len(kids)} comments")

                    if not comment or comment.get("deleted") or not comment.get("text"):
                        return None

                    text = comment["text"]
                    soup = BeautifulSoup(text, "html.parser")
                    plain_text = soup.get_text(separator="\n")
                    lines = [l.strip() for l in plain_text.split("\n") if l.strip()]

                    if not lines:
                        return None

                    header = parse_hiring_header(text)
                    # Ambiguous posts remain reviewable; do not invent a role.
                    company = header["company"] if header else lines[0].split("|")[0].strip()
                    title = header["title"] if header else ""
                    location = header["location"] if header else ""

                    listing = JobListing(
                        title=title,
                        company=company,
                        location=location,
                        description=plain_text,
                        url=f"https://news.ycombinator.com/item?id={kid_id}",
                        source=self.source_name,
                        posted_date=datetime.fromtimestamp(comment["time"], timezone.utc).isoformat() if comment.get("time") else None,
                    )
                    self._partial_results.append(listing)
                    return listing

            results = await asyncio.gather(
                *(fetch_comment(kid_id) for kid_id in kids),
                return_exceptions=True,
            )

            jobs = [r for r in results if isinstance(r, JobListing)]

        logger.info(f"HN scraper found {len(jobs)} jobs from {len(kids)} comments")
        return jobs
