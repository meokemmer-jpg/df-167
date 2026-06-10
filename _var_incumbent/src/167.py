from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Iterable, Mapping, Any


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"unsupported date value: {value!r}")


def _normalize_docs(documents: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for doc in documents:
        item = deepcopy(dict(doc))
        item["expires_on"] = _to_date(item.get("expires_on"))
        normalized.append(item)
    return normalized


def evaluate_document_compliance(
    documents: Iterable[Mapping[str, Any]],
    mandatory_doc_types: Iterable[str],
    *,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    """
    Compute compliance tracking metrics without modifying or deleting documents.

    Expected document fields:
    - doc_type: str
    - expires_on: ISO date string, date, or None
    """
    snapshot = _normalize_docs(documents)
    required = set(mandatory_doc_types)
    today = _to_date(as_of) if as_of is not None else date.today()

    total_docs_tracked = len(snapshot)
    expired_docs_count = sum(
        1 for doc in snapshot if doc.get("expires_on") is not None and doc["expires_on"] < today
    )

    present_doc_types = {str(doc.get("doc_type")) for doc in snapshot if doc.get("doc_type")}
    missing_mandatory_docs = sorted(required - present_doc_types)

    valid_required_docs = 0
    for doc_type in required:
        matching = [doc for doc in snapshot if doc.get("doc_type") == doc_type]
        if any(doc.get("expires_on") is None or doc["expires_on"] >= today for doc in matching):
            valid_required_docs += 1

    mandatory_coverage_pct = 100.0 if not required else (valid_required_docs / len(required)) * 100.0
    expired_penalty_pct = 0.0 if total_docs_tracked == 0 else (expired_docs_count / total_docs_tracked) * 100.0
    compliance_score_pct = round(max(0.0, mandatory_coverage_pct - expired_penalty_pct), 2)

    return {
        "total_docs_tracked": total_docs_tracked,
        "expired_docs_count": expired_docs_count,
        "missing_mandatory_docs": missing_mandatory_docs,
        "compliance_score_pct": compliance_score_pct,
        "as_of": today.isoformat(),
    }
# [CRUX-MK]
