
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-167 LexVance document compliance tracker."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-167.lock")
DF_ID = "167"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-167"
    iso_timestamp: str = ""
    source: str = "mock"
    documents_total: int = 0
    completion_rate_pct: float = 0.0
    missing_per_client: dict = field(default_factory=dict)
    oldest_pending: str = ""
    expiring_documents_30d: int = 0


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False

    try:
        first = p.stat()
        age = time.time() - first.st_mtime
        if age < min_age_sec:
            return False
        time.sleep(0.05)
        second = p.stat()
        return first.st_size == second.st_size and first.st_mtime == second.st_mtime
    except OSError:
        return False


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60

    try:
        LOCK_DIR.mkdir(mode=0o700)
        _write_lock_identity()
        return True
    except FileExistsError:
        pass
    except OSError:
        return False

    try:
        age = time.time() - LOCK_DIR.stat().st_mtime
        if age <= stale_after_sec:
            return False

        for item in LOCK_DIR.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
        LOCK_DIR.rmdir()
        LOCK_DIR.mkdir(mode=0o700)
        _write_lock_identity()
        return True
    except OSError:
        return False


def _write_lock_identity() -> None:
    identity = {
        "df": f"DF-{DF_ID}",
        "pid": os.getpid(),
        "created_at": iso_now(),
        "cwd": str(Path.cwd()),
    }
    (LOCK_DIR / "identity.json").write_text(
        json.dumps(identity, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def release_lock() -> None:
    try:
        for item in LOCK_DIR.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
        LOCK_DIR.rmdir()
    except FileNotFoundError:
        return
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors or []:
        value = str(anchor).strip()
        if not value:
            continue

        env_value = os.environ.get(value)
        if env_value:
            candidate = Path(env_value)
        else:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = DF_DIR / candidate

        if not candidate.exists():
            missing.append(value)

    env_tag = os.environ.get("DF_167_ENV_TAG", "local")
    return {
        "ok": len(missing) == 0,
        "missing_anchors": missing,
        "env_tag": env_tag,
    }


def _is_real_api_enabled() -> bool:
    value = os.environ.get("DF_167_REAL_API_ENABLED", "false")
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    return sorted({match.group(0).lower() for match in DECISION_KEYWORDS_REGEX.finditer(str(text))})


def assert_no_decision_keywords(output) -> None:
    if isinstance(output, str):
        text = output
    else:
        text = json.dumps(output, ensure_ascii=True, sort_keys=True)

    hits = scan_output_for_decision_keywords(text)
    if hits:
        raise ValueError("Q_0/K_0 blocked terms found: " + ", ".join(hits))


def collect_tracker_output() -> TrackerOutput:
    now = iso_now()
    data = TrackerOutput(iso_timestamp=now)

    env_payload = os.environ.get("DF_167_MOCK_PAYLOAD_JSON", "").strip()
    if env_payload:
        payload = json.loads(env_payload)
        data.documents_total = int(payload.get("documents_total", 0))
        data.completion_rate_pct = float(payload.get("completion_rate_pct", 0.0))
        data.missing_per_client = dict(payload.get("missing_per_client", {}))
        data.oldest_pending = str(payload.get("oldest_pending", ""))
        data.expiring_documents_30d = int(payload.get("expiring_documents_30d", 0))
        return data

    input_path = os.environ.get("DF_167_MOCK_PAYLOAD_FILE", "").strip()
    if input_path:
        p = Path(input_path)
        if p.exists() and _file_stable(p, min_age_sec=0):
            payload = json.loads(p.read_text(encoding="utf-8"))
            data.documents_total = int(payload.get("documents_total", 0))
            data.completion_rate_pct = float(payload.get("completion_rate_pct", 0.0))
            data.missing_per_client = dict(payload.get("missing_per_client", {}))
            data.oldest_pending = str(payload.get("oldest_pending", ""))
            data.expiring_documents_30d = int(payload.get("expiring_documents_30d", 0))
            return data

    if _is_real_api_enabled():
        data.source = "real_unavailable"

    return data


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        pav = k17_pre_action_verification([])
        if not pav.get("ok"):
            report = {
                "welle": "25",
                "df": "DF-167",
                "iso_timestamp": iso_now(),
                "source": "precheck",
                "status": "blocked",
                "k17_pre_action_verification": pav,
            }
            assert_no_decision_keywords(report)
            _write_report(report)
            return 3

        output = collect_tracker_output()
        report = asdict(output)
        report["k17_pre_action_verification"] = pav
        report["df_id"] = DF_ID

        assert_no_decision_keywords(report)
        _write_report(report)
        return 0
    except Exception as exc:
        error_report = {
            "welle": "25",
            "df": "DF-167",
            "iso_timestamp": iso_now(),
            "source": "runtime",
            "status": "error",
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
        try:
            assert_no_decision_keywords(error_report)
            _write_report(error_report)
        except Exception:
            pass
        return 3
    finally:
        release_lock()


def _write_report(report: dict) -> Path:
    reports_dir = DF_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = reports_dir / f"df-167-{date_tag}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


if __name__ == "__main__":
    sys.exit(main())