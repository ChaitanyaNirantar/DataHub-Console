"""
Data preparation: clean, validate, and preprocess incoming records
before they're allowed into DataHub.

Every record either passes and gets typed/normalized, or gets routed
to a quarantine list with a reason -- so nothing silently corrupts
the dataset, and every drop is auditable.
"""

import logging
from typing import List, Dict, Any, Tuple

from schema import FIELD_SPEC

log = logging.getLogger("clean")


def _coerce(value, py_type):
    if value is None:
        return None
    try:
        return py_type(value)
    except (ValueError, TypeError):
        raise ValueError(f"cannot coerce {value!r} to {py_type}")


def validate_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    for field, (py_type, nullable) in FIELD_SPEC.items():
        if field not in record:
            return False, f"missing field '{field}'"
        val = record[field]
        if val is None:
            if not nullable:
                return False, f"field '{field}' is required but null"
            continue
        try:
            _coerce(val, py_type)
        except ValueError as e:
            return False, str(e)
    if record.get("stars", 0) < 0 or record.get("forks", 0) < 0:
        return False, "negative stars/forks -- corrupt record"
    return True, ""


def clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(record)
    for field, (py_type, nullable) in FIELD_SPEC.items():
        if cleaned.get(field) is not None:
            cleaned[field] = _coerce(cleaned[field], py_type)
    if cleaned.get("description"):
        cleaned["description"] = cleaned["description"].strip().replace("\n", " ")[:500]
    if cleaned.get("full_name"):
        cleaned["full_name"] = cleaned["full_name"].strip()
    return cleaned


def clean_batch(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (clean_records, quarantined) where quarantined items carry a 'reason'."""
    good, bad = [], []
    seen_ids = set()
    for r in records:
        ok, reason = validate_record(r)
        if not ok:
            bad.append({**r, "reason": reason})
            continue
        if r["repo_id"] in seen_ids:
            bad.append({**r, "reason": "duplicate repo_id"})
            continue
        seen_ids.add(r["repo_id"])
        good.append(clean_record(r))
    log.info("Cleaned batch: %s good, %s quarantined", len(good), len(bad))
    return good, bad
