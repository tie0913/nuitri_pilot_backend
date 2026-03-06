import os
import json
from pathlib import Path
import pytest

from src.ai.service import get_suggestions

BASELINE_PATH = Path("tests/ai_eval/golden_baseline.json")
CASES_PATH = Path("tests/ai_eval/golden_cases.json")

# If set, we overwrite stored snapshots with current outputs (intentional re-baseline)
RESET_BASELINE = os.getenv("RESET_BASELINE", "0") == "1"


def _load_cases(raw):
    # supports: [ {...} ] or { "cases": [ {...} ] } or dict-of-dicts
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("cases"), list):
            return raw["cases"]
        vals = list(raw.values())
        if vals and isinstance(vals[0], dict):
            return vals
    return []


def _norm_list(xs):
    if not isinstance(xs, list):
        return []
    return [str(x).strip() for x in xs if isinstance(x, str) and x.strip()]


def _overlap_count(a, b):
    sa = {x.lower() for x in _norm_list(a)}
    sb = {x.lower() for x in _norm_list(b)}
    return len(sa.intersection(sb))


@pytest.mark.ai_live
def test_ai_regression_against_baseline_live():
    assert BASELINE_PATH.exists(), "Missing tests/ai_eval/golden_baseline.json"
    assert CASES_PATH.exists(), "Missing tests/ai_eval/golden_cases.json"

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    raw_cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = _load_cases(raw_cases)

    assert isinstance(baseline, dict)
    assert isinstance(cases, list) and len(cases) > 0, "golden_cases.json parsed to empty list"

    baseline_cases = {c["id"]: c for c in baseline.get("cases", []) if isinstance(c, dict) and c.get("id")}

    failures = []
    baseline_changed = False  # if True (and no failures), we write baseline back

    for idx, c in enumerate(cases, start=1):
        if not isinstance(c, dict):
            failures.append(f"case#{idx}: invalid case format (expected dict)")
            continue

        cid = str(c.get("id") or c.get("case_id") or c.get("name") or f"case_{idx:03d}").strip()

        b = baseline_cases.get(cid)
        if not b:
            failures.append(f"baseline missing id={cid}")
            continue

        res = get_suggestions(c.get("user_profile", {}), c.get("goal", ""), client=None)
        if not res.success or not res.data:
            failures.append(f"{cid}: AI call failed: {res.error}")
            continue

        # Text pipeline schema
        recs = _norm_list(res.data.get("recommendations", []))
        warns = _norm_list(res.data.get("warnings", []))
        joined = " ".join([*recs, *warns]).lower()

        expected = b.get("expected", {}) if isinstance(b.get("expected"), dict) else {}
        must_any = expected.get("must_contain_any", [])
        must_not = expected.get("must_not_contain_any", [])

        # -----------------------------
        # 1) Guardrails (content)
        # -----------------------------
        if must_any:
            if not any(str(x).lower() in joined for x in must_any):
                failures.append(f"{cid}: missing required concept: one of {must_any}")

        if must_not:
            for bad in must_not:
                if str(bad).lower() in joined:
                    failures.append(f"{cid}: contains banned concept '{bad}'")
                    break

        # -----------------------------
        # 2) Shape checks
        # -----------------------------
        if len(recs) < 5:
            failures.append(f"{cid}: recommendations too short (expected >= 5, got {len(recs)})")
        if len(recs) > 12:
            failures.append(f"{cid}: recommendations too long (expected <= 12, got {len(recs)})")

        if len(warns) > 5:
            failures.append(f"{cid}: warnings too long (expected <= 5, got {len(warns)})")

        # -----------------------------
        # 3) Snapshot-based drift
        # -----------------------------
        snap = b.get("snapshot")

        # If missing snapshot OR reset requested -> write snapshot from current run
        if RESET_BASELINE or not isinstance(snap, dict):
            b["snapshot"] = {"recommendations": recs, "warnings": warns}
            baseline_changed = True
            continue

        # Drift enforcement
        prev_recs = snap.get("recommendations", [])
        prev_warns = snap.get("warnings", [])

        min_overlap = int(expected.get("min_recommendation_overlap", 2))
        overlap = _overlap_count(prev_recs, recs)

        if overlap < min_overlap:
            failures.append(f"{cid}: drift too high (recommendation overlap {overlap} < {min_overlap})")

        if isinstance(prev_warns, list) and len(_norm_list(prev_warns)) > 0 and len(warns) == 0:
            failures.append(f"{cid}: warnings drifted to empty (previous run had warnings)")

    # Write updated baseline only if:
    # - we changed snapshots AND
    # - the run had no failures
    if baseline_changed and not failures:
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2), encoding="utf-8")

    assert not failures, "AI regression failures:\n" + "\n".join(failures)