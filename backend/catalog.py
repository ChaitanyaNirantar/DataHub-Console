"""
Data cataloguing: builds a machine-readable + human-readable catalog
entry for a dataset -- field definitions, quality stats, provenance,
and freshness. This is the artifact that makes a dataset discoverable
and understandable by other researchers, per the JD.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from schema import FIELD_SPEC

CATALOG_DIR = Path(__file__).parent.parent / "data"


def _null_rate(records: List[Dict[str, Any]], field: str) -> float:
    if not records:
        return 0.0
    nulls = sum(1 for r in records if r.get(field) is None)
    return round(nulls / len(records), 4)


def build_catalog_entry(
    dataset_name: str,
    source: str,
    records: List[Dict[str, Any]],
    quarantined_count: int,
) -> Dict[str, Any]:
    fields = []
    for name, (py_type, nullable) in FIELD_SPEC.items():
        fields.append({
            "name": name,
            "type": py_type.__name__,
            "nullable": nullable,
            "null_rate": _null_rate(records, name),
        })

    entry = {
        "dataset_name": dataset_name,
        "source": source,
        "description": "Public GitHub repository metadata, sourced via the GitHub Search API.",
        "row_count": len(records),
        "quarantined_count": quarantined_count,
        "fields": fields,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "primary_key": "repo_id",
        "refresh_method": "scraper.GitHubScraper.fetch (manual or scheduled)",
    }
    return entry


def write_catalog(entry: Dict[str, Any]):
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    json_path = CATALOG_DIR / f"{entry['dataset_name']}_catalog.json"
    md_path = CATALOG_DIR / f"{entry['dataset_name']}_catalog.md"

    json_path.write_text(json.dumps(entry, indent=2))

    lines = [
        f"# Dataset Catalog: {entry['dataset_name']}",
        "",
        f"- **Source:** {entry['source']}",
        f"- **Description:** {entry['description']}",
        f"- **Row count:** {entry['row_count']}",
        f"- **Quarantined records:** {entry['quarantined_count']}",
        f"- **Primary key:** {entry['primary_key']}",
        f"- **Last updated (UTC):** {entry['last_updated_utc']}",
        "",
        "## Fields",
        "",
        "| Field | Type | Nullable | Null rate |",
        "|---|---|---|---|",
    ]
    for f in entry["fields"]:
        lines.append(f"| {f['name']} | {f['type']} | {f['nullable']} | {f['null_rate']} |")
    md_path.write_text("\n".join(lines))
    return json_path, md_path
