"""
Data sourcing: pulls repository metadata from the GitHub REST API.

This stands in for the "identify, scrape, and integrate new external
datasets via APIs" responsibility in the JD. GitHub's search API is
used here because it's free, well-documented, and doesn't require
auth for light usage (60 req/hr unauthenticated, 5000/hr with a token).
"""

import time
import logging
from typing import List, Dict, Any, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scraper")

GITHUB_API = "https://api.github.com/search/repositories"


class GitHubScraper:
    def __init__(self, token: Optional[str] = None, per_page: int = 30):
        self.per_page = per_page
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)

    def fetch(self, query: str, max_pages: int = 3, sleep_s: float = 1.0) -> List[Dict[str, Any]]:
        """Fetch repos matching `query`, sorted by stars, across up to max_pages."""
        results: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": self.per_page,
                "page": page,
            }
            resp = self.session.get(GITHUB_API, params=params, timeout=15)
            if resp.status_code == 403:
                log.warning("Rate limited by GitHub API, stopping early at page %s", page)
                break
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                break
            log.info("Fetched page %s: %s repos", page, len(items))
            results.extend(items)
            time.sleep(sleep_s)  # be a polite scraper
        return results

    @staticmethod
    def to_raw_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Project the huge GitHub payload down to the fields we care about."""
        raw = []
        for it in items:
            raw.append({
                "repo_id": it.get("id"),
                "full_name": it.get("full_name"),
                "description": it.get("description"),
                "language": it.get("language"),
                "stars": it.get("stargazers_count"),
                "forks": it.get("forks_count"),
                "open_issues": it.get("open_issues_count"),
                "created_at": it.get("created_at"),
                "pushed_at": it.get("pushed_at"),
                "license": (it.get("license") or {}).get("spdx_id") if it.get("license") else None,
                "url": it.get("html_url"),
            })
        return raw


if __name__ == "__main__":
    scraper = GitHubScraper()
    raw = scraper.fetch("topic:machine-learning language:python", max_pages=2)
    records = scraper.to_raw_records(raw)
    log.info("Collected %s raw records", len(records))
    print(records[:2])
