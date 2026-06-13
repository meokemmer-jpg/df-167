from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

STOP_FLAG = Path("/tmp/df-167.stop")


@dataclass(frozen=True)
class ComplianceSummary:
    total_docs_tracked: int
    expired_docs_count: int
    missing_mandatory_docs: List[str]
    compliance_score_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_docs_tracked": self.total_docs_tracked,
            "expired_docs_count": self.expired_docs_count,
            "missing_mandatory_docs": list(self.missing_mandatory_docs),
            "compliance_score_pct": self.compliance_score_pct,
        }


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None
    return date.fromisoformat(value)


def _is_expired(expires_on: Optional[str], as_of: date) -> bool:
    parsed = _parse_iso_date(expires_on)
    return parsed is not None and parsed < as_of


def evaluate_compliance(
    documents: Sequence[Dict[str, Any]],
    mandatory_doc_types: Iterable[str],
    *,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Compute compliance tracking metrics without mutating the input documents.

    Expected document shape:
    {
        "doc_type": "business_license",
        "expires_on": "2026-12-31" | None,
        ...
    }
    """
    as_of = as_of or date.today()
    docs = deepcopy(list(documents))
    mandatory = list(dict.fromkeys(mandatory_doc_types))

    present_types = {
        str(doc["doc_type"])
        for doc in docs
        if "doc_type" in doc and doc["doc_type"] not in (None, "")
    }

    expired_count = sum(
        1 for doc in docs if _is_expired(doc.get("expires_on"), as_of)
    )
    missing = [doc_type for doc_type in mandatory if doc_type not in present_types]

    mandatory_score = (
        ((len(mandatory) - len(missing)) / len(mandatory)) * 100.0 if mandatory else 100.0
    )
    freshness_score = (
        ((len(docs) - expired_count) / len(docs)) * 100.0 if docs else 100.0
    )
    compliance_score = round((mandatory_score + freshness_score) / 2.0, 2)

    summary = ComplianceSummary(
        total_docs_tracked=len(docs),
        expired_docs_count=expired_count,
        missing_mandatory_docs=missing,
        compliance_score_pct=compliance_score,
    )
    return summary.to_dict()


def build_report(
    documents: Sequence[Dict[str, Any]],
    mandatory_doc_types: Iterable[str],
    *,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    as_of = as_of or date.today()
    report = evaluate_compliance(documents, mandatory_doc_types, as_of=as_of)
    report["report_date"] = as_of.isoformat()
    report["stop_requested"] = STOP_FLAG.exists()
    return report


def write_report(
    documents: Sequence[Dict[str, Any]],
    mandatory_doc_types: Iterable[str],
    output_dir: str | Path = "reports",
    *,
    as_of: Optional[date] = None,
) -> Path:
    as_of = as_of or date.today()
    report = build_report(documents, mandatory_doc_types, as_of=as_of)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / f"df-167-{as_of.isoformat()}.json"
    file_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return file_path
# [CRUX-MK]
