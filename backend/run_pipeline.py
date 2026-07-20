"""
Orchestrates the full onboarding flow for a new dataset:
scrape -> clean/validate -> load into DataHub -> catalog it.

Usage:
    python run_pipeline.py --query "topic:machine-learning language:python" --pages 2
"""

import argparse
import logging

from scraper import GitHubScraper
from clean import clean_batch
from db import init_db, upsert_records, row_count
from catalog import build_catalog_entry, write_catalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pipeline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="topic:machine-learning language:python")
    parser.add_argument("--pages", type=int, default=2)
    args = parser.parse_args()

    init_db()

    log.info("Sourcing data from GitHub API...")
    scraper = GitHubScraper()
    raw_items = scraper.fetch(args.query, max_pages=args.pages)
    raw_records = scraper.to_raw_records(raw_items)

    log.info("Validating and cleaning %s raw records...", len(raw_records))
    clean, quarantined = clean_batch(raw_records)

    log.info("Loading %s clean records into DataHub...", len(clean))
    upsert_records(clean)

    log.info("Building catalog entry...")
    entry = build_catalog_entry("github_repos", "GitHub Search API", clean, len(quarantined))
    json_path, md_path = write_catalog(entry)

    log.info("Done. DataHub now has %s total rows.", row_count())
    log.info("Catalog written to %s and %s", json_path, md_path)
    if quarantined:
        log.warning("Quarantined %s records, e.g.: %s", len(quarantined), quarantined[0])


if __name__ == "__main__":
    main()
