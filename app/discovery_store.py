"""Candidate-local discovery audit and persistent scoring retry state."""
import json
from datetime import datetime, timedelta, timezone

from app.discovery import canonical_url, content_fingerprint, plain, quality_issues, same_listing


class DiscoveryStore:
    async def assess_listing(self, job_id: int):
        job = await self.get_job(job_id)
        if not job:
            return
        issues = quality_issues(job)
        await self.db.execute("UPDATE jobs SET quality_status=?, quality_reasons=?,content_fingerprint=? WHERE id=?",
                              ("review" if issues else "ready", json.dumps(issues), content_fingerprint(job), job_id))
        await self.db.commit()

    async def audit_discovery(self) -> dict:
        from app.scrapers.hackernews import parse_hiring_header
        cursor = await self.db.execute("SELECT * FROM jobs WHERE dismissed=0 ORDER BY id")
        jobs = [dict(row) for row in await cursor.fetchall()]
        seen_urls, seen_content = {}, {}
        counts = {"checked": len(jobs), "repaired": 0, "review": 0, "duplicates": 0}
        for job in jobs:
            if "news.ycombinator.com/item?" in job["url"] and quality_issues(job):
                parsed = parse_hiring_header(job["description"])
                if parsed and not quality_issues({**job, **parsed}):
                    # Recheck classification when repairing the field it depended on.
                    from app.location_classifier import classify_location_rule_based
                    region = classify_location_rule_based(parsed["location"])
                    await self.db.execute("UPDATE jobs SET title=?,company=?,location=?,location_region=?,location_classified=? WHERE id=?",
                                          (parsed["title"], parsed["company"], parsed["location"], region, int(region is not None), job["id"]))
                    job.update(parsed)
                    counts["repaired"] += 1
            issues = quality_issues(job)
            url = canonical_url(job["url"])
            key = tuple(plain(job[k]).casefold() for k in ("title", "company", "location", "description"))
            prior = seen_urls.get(url) if url else None
            if not prior:
                prior = next((p for p in seen_content.get(key, []) if same_listing(p, job)), None)
            duplicate = prior["id"] if prior else None
            if url and not prior:
                seen_urls[url] = job
            seen_content.setdefault(key, []).append(job)
            await self.db.execute("UPDATE jobs SET quality_status=?,quality_reasons=?,duplicate_of=?,canonical_url=?,content_fingerprint=? WHERE id=?",
                                  ("review" if issues else "ready", json.dumps(issues), duplicate, url, content_fingerprint(job), job["id"]))
            counts["review"] += bool(issues)
            counts["duplicates"] += bool(duplicate)
        await self.db.commit()
        return counts

    async def find_exact_listing(self, listing: dict) -> dict | None:
        cursor = await self.db.execute("""SELECT * FROM jobs WHERE duplicate_of IS NULL AND
            ((canonical_url!='' AND canonical_url=?) OR (content_fingerprint!='' AND content_fingerprint=?)) ORDER BY id""",
            (canonical_url(listing.get("url", "")), content_fingerprint(listing)))
        for row in await cursor.fetchall():
            existing = dict(row)
            if same_listing(existing, listing):
                return existing
        return None

    async def record_scoring_failure(self, job_id: int, code: str):
        now = datetime.now(timezone.utc)
        job = await self.get_job(job_id)
        attempts = (job.get("scoring_attempts") or 0) + 1
        validation_failures = (job.get("scoring_validation_failures") or 0) + int(code == "invalid_model_response")
        review = validation_failures >= 3
        retry_at = now + timedelta(minutes=min(1440, 15 * 2 ** min(attempts - 1, 7)))
        await self.db.execute(
            """UPDATE jobs SET scoring_attempts=?, scoring_last_error=?, scoring_attempted_at=?,
               scoring_retry_at=?, scoring_review_required=?, scoring_validation_failures=? WHERE id=?""",
            (attempts, code, now.isoformat(), retry_at.isoformat(), int(review), validation_failures, job_id))
        await self.db.commit()

    async def reset_scoring_retry(self, job_id: int):
        await self.db.execute("""UPDATE jobs SET scoring_attempts=0,scoring_validation_failures=0,scoring_last_error=NULL,
            scoring_retry_at=NULL,scoring_review_required=0 WHERE id=?""", (job_id,))
        await self.db.commit()

    async def save_availability(self, job_id: int, result: dict):
        await self.db.execute("""UPDATE jobs SET availability_status=?, availability_reason=?,
            availability_checked_at=? WHERE id=?""",
            (result["status"], result["reason"], result["checked_at"], job_id))
        await self.db.commit()

    async def discovery_summary(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute("""SELECT
            COUNT(*) AS active_jobs,
            SUM(j.quality_status='review') AS quality_review,
            SUM(j.duplicate_of IS NOT NULL) AS duplicates,
            SUM(j.availability_status='closed') AS closed,
            SUM(j.availability_checked_at IS NOT NULL) AS availability_checked,
            SUM(s.id IS NULL AND j.location_classified=1) AS unscored,
            SUM(s.id IS NULL AND j.location_classified=1 AND j.quality_status!='review'
                AND j.duplicate_of IS NULL AND j.availability_status!='closed'
                AND j.scoring_review_required=0 AND (j.scoring_retry_at IS NULL OR j.scoring_retry_at<=?)) AS ready,
            SUM(s.id IS NULL AND j.scoring_review_required=1) AS scoring_review,
            SUM(s.id IS NULL AND j.scoring_review_required=0 AND j.scoring_retry_at>?) AS cooling_down
            FROM jobs j LEFT JOIN job_scores s ON j.id=s.job_id WHERE j.dismissed=0""", (now, now))
        summary = {k: v or 0 for k, v in dict(await cursor.fetchone()).items()}
        cursor = await self.db.execute("""SELECT id,title,quality_status,quality_reasons,duplicate_of,
            availability_status,availability_reason,scoring_last_error,scoring_review_required
            FROM jobs WHERE dismissed=0 AND (quality_status='review' OR duplicate_of IS NOT NULL
            OR availability_status='closed' OR scoring_last_error IS NOT NULL) ORDER BY id LIMIT 25""")
        summary["review_jobs"] = [dict(row) for row in await cursor.fetchall()]
        return summary
