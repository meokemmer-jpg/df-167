from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping, Any, Optional


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None
    return date.fromisoformat(value)


def evaluate_compliance(
    documents: Iterable[Mapping[str, Any]],
    mandatory_doc_types: Iterable[str],
    as_of: Optional[str] = None,
) -> dict[str, Any]:
    """
    Read-only compliance tracking for legal documents.

    Each document is a mapping with:
    - "doc_type": str
    - "expires_on": ISO date string or None

    The function never mutates input data and never makes compliance decisions.
    It only reports tracking metrics.
    """
    effective_date = _parse_date(as_of) if as_of else date.today()
    mandatory = set(mandatory_doc_types)

    total_docs_tracked = 0
    expired_docs_count = 0
    present_doc_types = set()

    for doc in documents:
        total_docs_tracked += 1

        doc_type = doc.get("doc_type")
        if doc_type:
            present_doc_types.add(doc_type)

        expires_on = _parse_date(doc.get("expires_on"))
        if expires_on is not None and expires_on < effective_date:
            expired_docs_count += 1

    missing_mandatory_docs = sorted(mandatory - present_doc_types)

    score_parts = [
        0 if expired_docs_count else 50,
        0 if missing_mandatory_docs else 50,
    ]
    compliance_score_pct = sum(score_parts)

    return {
        "total_docs_tracked": total_docs_tracked,
        "expired_docs_count": expired_docs_count,
        "missing_mandatory_docs": missing_mandatory_docs,
        "compliance_score_pct": compliance_score_pct,
        "as_of": effective_date.isoformat(),
        "read_only": True,
    }
# [CRUX-MK]
