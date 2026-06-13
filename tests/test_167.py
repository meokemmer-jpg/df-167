import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import copy
import importlib

m167 = importlib.import_module("167")
evaluate_compliance = m167.evaluate_compliance
write_report = m167.write_report


def test_evaluate_compliance_and_write_report(tmp_path):
    documents = [
        {"doc_type": "business_license", "expires_on": "2030-01-01"},
        {"doc_type": "insurance_certificate", "expires_on": "2024-01-01"},
        {"doc_type": "safety_audit", "expires_on": None},
    ]
    original = copy.deepcopy(documents)

    result = evaluate_compliance(
        documents,
        ["business_license", "insurance_certificate", "tax_certificate"],
        as_of=m167.date(2026, 6, 12),
    )

    assert result["total_docs_tracked"] == 3
    assert result["expired_docs_count"] == 1
    assert result["missing_mandatory_docs"] == ["tax_certificate"]
    assert result["compliance_score_pct"] == 66.67
    assert documents == original

    report_path = write_report(
        documents,
        ["business_license", "insurance_certificate", "tax_certificate"],
        output_dir=tmp_path,
        as_of=m167.date(2026, 6, 12),
    )

    assert report_path.name == "df-167-2026-06-12.json"
    payload = report_path.read_text(encoding="utf-8")
    assert '"report_date": "2026-06-12"' in payload
    assert '"expired_docs_count": 1' in payload
