"""Conservative listing quality, identity and availability checks."""
import asyncio
import hashlib
import ipaddress
import json
import re
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)).strip()


def canonical_url(url: str) -> str:
    """Remove tracking only; preserve requisition IDs, path case and identity queries."""
    try:
        p = urlsplit(url.strip())
        if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
            return ""
        tracking = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
                    "gclid", "fbclid", "msclkid", "trk", "trackingid"}
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in tracking]
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", urlencode(sorted(query)), ""))
    except ValueError:
        return ""


ROLE = re.compile(r"\b(engineer|developer|architect|manager|designer|analyst|scientist|director|specialist|consultant|lead|researcher|administrator|recruiter|accountant|sales|marketing|support|devops|sre|intern|technician|nurse|officer|counsel|writer|founder)\b", re.I)


def quality_issues(job: dict) -> list[str]:
    title, company, description = (plain(job.get(k, "")) for k in ("title", "company", "description"))
    issues = []
    if not title or len(title) < 3:
        issues.append("Missing job title")
    elif len(title) > 180 or title.startswith(("http://", "https://")):
        issues.append("Title appears to contain page content or a URL")
    elif title.casefold() == company.casefold() or title.count("(") != title.count(")"):
        issues.append("Incomplete or ambiguous job title")
    elif not ROLE.search(title) and re.search(r"\b(remote|onsite|on-site|hybrid|emea|apac|uk|usa|london|zurich)\b", title, re.I):
        issues.append("Title appears to be a location or work arrangement")
    if not company:
        issues.append("Missing company")
    if len(description) < 80:
        issues.append("Description too short to establish job duties")
    if not canonical_url(job.get("url", "")) and not job.get("url", "").startswith("external://"):
        issues.append("Invalid listing URL")
    return issues


def same_listing(a: dict, b: dict) -> bool:
    ca, cb = canonical_url(a.get("url", "")), canonical_url(b.get("url", ""))
    if ca and ca == cb:
        return True
    # Similar titles alone are not identity: different cities/requisitions survive.
    if any(plain(a.get(k, "")).casefold() != plain(b.get(k, "")).casefold()
           for k in ("title", "company", "location")):
        return False
    da, db = plain(a.get("description", "")), plain(b.get("description", ""))
    if len(da) < 200 or da.casefold() != db.casefold():
        return False
    # Same-host distinct URLs commonly mean separate requisitions with boilerplate.
    return bool(ca and cb and urlsplit(ca).hostname != urlsplit(cb).hostname)


def content_fingerprint(job: dict) -> str:
    if len(plain(job.get("description", ""))) < 200:
        return ""
    content = [plain(job.get(k, "")).casefold() for k in ("title", "company", "location", "description")]
    return hashlib.sha256(json.dumps(content).encode()).hexdigest()


async def public_url(url: str) -> bool:
    try:
        p = urlsplit(url)
        if not canonical_url(url) or p.port not in (None, 80, 443):
            return False
        addresses = await asyncio.get_running_loop().getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)
    except (ValueError, OSError):
        return False


def availability_from_response(status: int, body: str, job: dict, redirected: bool = False) -> tuple[str, str]:
    if status in {404, 410}:
        return "closed", f"Listing URL returned HTTP {status}"
    if status != 200:
        return "unknown", f"HTTP {status}; availability could not be verified"
    soup = BeautifulSoup(body, "html.parser")
    heading = " ".join(plain(t.get_text(" ")) for t in soup.select("title, h1, h2"))
    if re.search(r"(?:job|position|opening|vacancy) (?:is |has been )?(?:no longer available|closed|filled|expired)|no longer accepting applications", heading, re.I):
        return "closed", "Page heading explicitly reports this listing closed"
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in list(nodes):
            if isinstance(node, dict):
                nodes.extend(node.get("@graph", []) if isinstance(node.get("@graph"), list) else [])
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") != "JobPosting":
                continue
            if plain(node.get("title", "")).casefold() != plain(job.get("title", "")).casefold():
                continue
            expires = node.get("validThrough")
            if expires:
                try:
                    deadline = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                    if deadline < datetime.now(timezone.utc):
                        return "closed", "Matching JobPosting metadata has expired"
                except (ValueError, TypeError):
                    return "unknown", "Matching listing has an unreadable expiry date"
            return "available", "Matching JobPosting metadata found; confirm before applying"
    return "unknown", ("Redirected page did not verify the listing" if redirected else
                       "Page reachable; open listing could not be verified")


async def check_availability(job: dict) -> dict:
    try:
        return await asyncio.wait_for(_check_url_availability(job), timeout=30)
    except asyncio.TimeoutError:
        return {"status": "unknown", "reason": "Availability check timed out", "checked_at": datetime.now(timezone.utc).isoformat()}


async def check_known_sources(db, job: dict) -> dict:
    """One dead board URL must not close an opening available on another source."""
    sources = await db.get_sources(job["id"])
    urls = list(dict.fromkeys([job["url"], *(s["source_url"] for s in sources)]))
    checked, identities = [], set()
    for url in urls:
        identity = canonical_url(url) or url
        if identity in identities:
            continue
        identities.add(identity)
        if len(checked) == 5:
            return {"status": "unknown", "reason": "Some alternate listing URLs remain unchecked", "checked_at": datetime.now(timezone.utc).isoformat()}
        result = await check_availability({**job, "url": url})
        checked.append(result)
        if result["status"] == "available":
            return result
    unknown = next((r for r in checked if r["status"] == "unknown"), None)
    return unknown or {**checked[-1], "reason": f"All {len(checked)} known listing URLs report closure. " + checked[-1]["reason"]}


async def _check_url_availability(job: dict) -> dict:
    url = job.get("url", "")
    result = {"status": "unknown", "reason": "Listing could not be checked", "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        async with httpx.AsyncClient(timeout=12, verify=ssl.create_default_context(), follow_redirects=False,
                                     headers={"User-Agent": "CareerPulse/1.0 listing availability check"}) as client:
            for hop in range(5):
                if not await public_url(url):
                    result["reason"] = "URL is not a supported public web address"
                    return result
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > 1_000_000:
                            result["reason"] = "Page exceeded the bounded availability check"
                            return result
                    result["status"], result["reason"] = availability_from_response(
                        response.status_code, content.decode(response.encoding or "utf-8", errors="replace"), job, hop > 0)
                    return result
            result["reason"] = "Too many redirects to verify listing"
    except (httpx.HTTPError, ValueError, OSError):
        result["reason"] = "Network or TLS error; availability remains unknown"
    return result
