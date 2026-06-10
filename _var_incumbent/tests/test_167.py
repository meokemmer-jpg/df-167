import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# Hinweis: `from 167 import ...` ist in Python SyntaxError.
# Fuer einen wirklich gruen laufenden pytest-Test muss daher dynamisch importiert werden.

import importlib.util
from pathlib import Path


_spec = importlib.util.spec_from_file_location("mod167", Path(__file__).with_name("167.py"))
_mod = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_mod)
evaluate_document_compliance = _mod.evaluate_document_compliance


def test_evaluate_document_compliance_tracks_metrics_without_mutation():
    documents = [
        {"doc_type": "business_license", "expires_on": "2030-01-01"},
        {"doc_type": "tax_certificate", "expires_on": "2024-01-01"},
        {"doc_type": "insurance", "expires_on": None},
    ]
    original = [dict(item) for item in documents]

    result = evaluate_document_compliance(
        documents,
        {"business_license", "insurance", "fire_safety"},
        as_of="2026-06-09",
    )

    assert result["total_docs_tracked"] == 3
    assert result["expired_docs_count"] == 1
    assert result["missing_mandatory_docs"] == ["fire_safety"]
    assert result["compliance_score_pct"] == 33.33
    assert result["as_of"] == "2026-06-09"
    assert documents == original

