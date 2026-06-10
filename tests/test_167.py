import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# `from 167 import ...` is invalid Python syntax because module names cannot start with a digit.
# This is the runnable stdlib equivalent for a file named `167.py`.
import importlib

mod = importlib.import_module("167")
evaluate_compliance = mod.evaluate_compliance


def test_evaluate_compliance_tracks_counts_and_score():
    documents = [
        {"doc_type": "license", "expires_on": "2030-01-01"},
        {"doc_type": "insurance", "expires_on": "2020-01-01"},
        {"doc_type": "nda", "expires_on": None},
    ]

    result = evaluate_compliance(
        documents,
        mandatory_doc_types=["license", "insurance", "tax_certificate"],
        as_of="2025-01-01",
    )

    assert result["total_docs_tracked"] == 3
    assert result["expired_docs_count"] == 1
    assert result["missing_mandatory_docs"] == ["tax_certificate"]
    assert result["compliance_score_pct"] == 0
    assert result["as_of"] == "2025-01-01"
    assert result["read_only"] is True
