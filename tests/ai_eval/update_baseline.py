import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union

BASELINE_PATH = Path("tests/ai_eval/golden_baseline.json")
CASES_PATH = Path("tests/ai_eval/golden_cases.json")


def _load_cases(raw: Any) -> List[Dict[str, Any]]:
    """
    Accept these formats:
      1) [ {case}, {case} ]
      2) { "cases": [ {case}, ... ] }
      3) { ... }  -> try common keys, else empty
      4) [ "string", ... ] -> convert to dict cases
    """
    # Format 1: list
    if isinstance(raw, list):
        if len(raw) == 0:
            return []
        # list of dicts
        if isinstance(raw[0], dict):
            return raw  # type: ignore
        # list of strings
        if isinstance(raw[0], str):
            return [{"id": s, "user_profile": {}, "goal": ""} for s in raw]
        return []

    # Format 2/3: dict
    if isinstance(raw, dict):
        # most common
        if isinstance(raw.get("cases"), list) and (len(raw["cases"]) == 0 or isinstance(raw["cases"][0], dict)):
            return raw["cases"]  # type: ignore

        # try other common keys
        for key in ["golden_cases", "items", "data", "examples"]:
            if isinstance(raw.get(key), list) and (len(raw[key]) == 0 or isinstance(raw[key][0], dict)):
                return raw[key]  # type: ignore

        # If dict of dicts (id -> case)
        # Iterating raw would yield keys, but values might be dict cases.
        values = list(raw.values())
        if values and isinstance(values[0], dict):
            return values  # type: ignore

    return []


def _case_id(case: Dict[str, Any], index: int) -> str:
    # Prefer explicit id; fallback to something deterministic
    return (
        str(case.get("id") or case.get("case_id") or case.get("name") or f"case_{index:03d}")
        .strip()
    )


def main():
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = _load_cases(raw)

    if not cases:
        raise SystemExit(
            f"Could not parse cases from {CASES_PATH}. "
            "Expected a list of dicts or an object with key 'cases'."
        )

    baseline = {
        "meta": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": str(CASES_PATH),
        },
        "cases": [],
    }

    for idx, c in enumerate(cases, start=1):
        cid = _case_id(c, idx)

        baseline["cases"].append(
            {
                "id": cid,
                "expected": {
                    # default guardrails (safe + stable)
                    "must_not_contain_any": ["cure", "detox", "miracle", "guarantee"],
                    # optional per-case expectations if present in golden_cases.json
                    "must_contain_any": c.get("must_contain_any", []),
                    "min_mark": c.get("min_mark", 0),
                    "max_mark": c.get("max_mark", 100),
                },
                "last_run": None,
            }
        )

    BASELINE_PATH.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"Wrote {BASELINE_PATH} with {len(baseline['cases'])} cases.")


if __name__ == "__main__":
    main()