import base64
import json
import os
import random
from datetime import datetime
from pathlib import Path

import pytest

# ✅ This is the correct import (matches your working regression test)
from src.ai.service import get_suggestions


IMAGES_DIR = Path(__file__).resolve().parent / "images"
RUNS_DIR = Path(__file__).resolve().parent / "runs"


def _load_images() -> list[Path]:
    assert IMAGES_DIR.exists(), f"Missing images dir: {IMAGES_DIR}"
    imgs: list[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        imgs.extend(IMAGES_DIR.glob(ext))
    assert imgs, f"No images found in {IMAGES_DIR} (add 10–20 jpg/png/webp images)"
    return sorted(imgs)


def _img_to_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def _norm_list(x) -> list[str]:
    if not x:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    s = str(x).strip()
    return [s] if s else []


def _write_run(tag: str, payload: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{tag}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _generate_profiles(n: int, seed: int) -> list[dict]:
    random.seed(seed)

    chronics_pool = [
        [],
        ["pcos"],
        ["thyroid"],
        ["prediabetes"],
        ["hypertension"],
    ]
    allergies_pool = [
        [],
        ["peanut"],
        ["lactose"],
        ["gluten"],
        ["soy"],
    ]
    goals = [
        "Analyze this food photo and suggest if it's suitable for me.",
        "Give healthier alternatives and portion guidance for this meal.",
        "Is this meal PCOS-friendly? Provide suggestions.",
        "High-protein vegetarian advice for this meal.",
        "Low sugar / low GI advice for this meal.",
    ]

    cases = []
    for i in range(1, n + 1):
        cases.append(
            {
                "id": f"case_{i:03d}",
                "goal": random.choice(goals),
                "user_profile": {
                    "chronics": random.choice(chronics_pool),
                    "allergies": random.choice(allergies_pool),
                },
            }
        )
    return cases


def _extract_recommendations(data: dict) -> list[str]:
    """
    Your codebase uses both:
      - recommendation (singular, photo pipeline)
      - recommendations (plural, some text pipeline tests)
    This keeps the batch test compatible with both.
    """
    if not isinstance(data, dict):
        return []
    if "recommendation" in data:
        return _norm_list(data.get("recommendation"))
    if "recommendations" in data:
        return _norm_list(data.get("recommendations"))
    return []


def _extract_warnings(data: dict) -> list[str]:
    """
    Some pipelines may return warnings; photo pipeline may not.
    Treat missing warnings as OK.
    """
    if not isinstance(data, dict):
        return []
    return _norm_list(data.get("warnings"))


def _extract_score_mark(data: dict):
    """
    Your photo pipeline uses: mark (score).
    """
    if not isinstance(data, dict):
        return None
    return data.get("mark", None)


@pytest.mark.ai_live
@pytest.mark.ai_batch
def test_ai_batch_100_outputs_live():
    """
    A) Batch robustness:
    - N cases (default 100)
    - Random image + random chronics/allergies each run
    - Validates: recommendation list exists, mark score exists + in range
    - Saves full run JSON to tests/ai_eval/runs/
    """
    n = int(os.getenv("AI_BATCH_N", "100"))
    max_fail = int(os.getenv("AI_BATCH_MAX_FAILURES", "5"))
    seed = int(os.getenv("AI_BATCH_SEED", "12345"))

    images = _load_images()
    cases = _generate_profiles(n, seed)

    failures: list[str] = []
    results: list[dict] = []
    fail_calls = 0

    for c in cases:
        img = random.choice(images)
        b64 = _img_to_b64(img)

        # Put the image where your app expects it (agent.get(base64_img, ...))
        user_profile = dict(c["user_profile"])
        user_profile["base64_img"] = b64

        res = get_suggestions(user_profile, c["goal"], client=None)

        item = {
            "id": c["id"],
            "image": img.name,
            "goal": c["goal"],
            "user_profile": c["user_profile"],  # without base64
            "success": getattr(res, "success", False),
            "error": getattr(res, "error", None),
            "data": getattr(res, "data", None),
        }

        # Call-level failure
        if not item["success"] or not item["data"]:
            fail_calls += 1
            failures.append(f"{c['id']}: AI call failed: {item['error']}")
            results.append(item)

            if fail_calls > max_fail:
                out = _write_run(f"batch_{n}_EARLY_STOP", {"failures": failures, "results": results})
                pytest.fail(f"Too many AI call failures (> {max_fail}). Saved: {out}")

            continue

        data = item["data"]
        recs = _extract_recommendations(data)
        warns = _extract_warnings(data)
        mark = _extract_score_mark(data)

        # Shape checks (match your contract more than the old test)
        if len(recs) < 3:
            failures.append(f"{c['id']}: recommendation list too short (expected >= 3, got {len(recs)})")
        if len(recs) > 12:
            failures.append(f"{c['id']}: recommendation list too long (expected <= 12, got {len(recs)})")

        if len(warns) > 10:
            failures.append(f"{c['id']}: warnings too long (expected <= 10, got {len(warns)})")

        # Score checks (mark should be numeric; typically 0–100)
        if mark is None:
            failures.append(f"{c['id']}: missing 'mark' score in response")
        else:
            try:
                m = float(mark)
                if not (0.0 <= m <= 100.0):
                    failures.append(f"{c['id']}: mark out of range 0–100 (got {m})")
            except Exception:
                failures.append(f"{c['id']}: mark not numeric (got {mark})")

        # Audit presence (your SuggestionService attaches audit)
        audit = data.get("audit")
        if audit is not None and isinstance(audit, dict):
            if "passed" not in audit:
                failures.append(f"{c['id']}: audit present but missing 'passed' key")

        item["normalized"] = {"recommendation": recs, "warnings": warns, "mark": mark, "audit": audit}
        results.append(item)

    out = _write_run(f"batch_{n}", {"failures": failures, "results": results})
    assert not failures, f"Batch failures ({len(failures)}). Saved: {out}\n" + "\n".join(failures[:50])


@pytest.mark.ai_live
@pytest.mark.ai_consistency
def test_ai_consistency_same_input_live():
    """
    B) Consistency:
    - Same image + same profile repeated N times (default 100)
    - Checks mark stability (std dev) + recommendation overlap
    """
    n = int(os.getenv("AI_CONSISTENCY_N", "100"))
    seed = int(os.getenv("AI_CONSISTENCY_SEED", "999"))
    max_std = float(os.getenv("AI_MARK_STD_MAX", "15"))
    overlap_min = int(os.getenv("AI_RECS_OVERLAP_MIN", "2"))

    images = _load_images()
    random.seed(seed)
    img = random.choice(images)
    b64 = _img_to_b64(img)

    fixed_profile = {"chronics": ["pcos"], "allergies": ["gluten"], "base64_img": b64}
    goal = "Analyze this food photo and give suggestions + score."

    runs: list[dict] = []
    failures: list[str] = []

    for i in range(1, n + 1):
        res = get_suggestions(fixed_profile, goal, client=None)
        data = getattr(res, "data", None) if getattr(res, "success", False) else None
        if not data:
            failures.append(f"run#{i}: AI call failed: {getattr(res, 'error', None)}")
            continue

        recs = _extract_recommendations(data)
        mark = _extract_score_mark(data)
        runs.append({"run": i, "recommendation": recs, "mark": mark})

    out = _write_run(f"consistency_{n}_{img.stem}", {"image": img.name, "runs": runs, "failures": failures})

    assert not failures, f"Consistency: some calls failed. Saved: {out}\n" + "\n".join(failures[:20])
    assert len(runs) == n, f"Consistency: expected {n} runs, got {len(runs)}. Saved: {out}"

    # Score stability
    marks: list[float] = []
    for r in runs:
        try:
            marks.append(float(r["mark"]))
        except Exception:
            failures.append(f"run#{r['run']}: mark not numeric (got {r['mark']})")

    assert not failures, f"Consistency mark failures. Saved: {out}\n" + "\n".join(failures[:20])

    mean = sum(marks) / len(marks)
    var = sum((m - mean) ** 2 for m in marks) / len(marks)
    std = var ** 0.5
    assert std <= max_std, f"Mark score too unstable (std={std:.2f} > {max_std}). Saved: {out}"

    # Recommendation overlap with run#1
    base = set(x.lower() for x in runs[0]["recommendation"])
    for r in runs[1:]:
        overlap = len(base.intersection(set(x.lower() for x in r["recommendation"])))
        if overlap < overlap_min:
            failures.append(f"run#{r['run']}: overlap too low ({overlap} < {overlap_min})")

    assert not failures, f"Recommendation overlap failures. Saved: {out}\n" + "\n".join(failures[:20])


@pytest.mark.ai_live
@pytest.mark.ai_judge
def test_ai_judge_quality_live():
    """
    C) Judge:
    Your app already runs audit via run_ai_audit and returns data['audit'].
    This test enforces that audit passes for most runs.
    Only runs if RUN_AI_JUDGE=1.
    """
    if os.getenv("RUN_AI_JUDGE") != "1":
        pytest.skip("RUN_AI_JUDGE!=1 (skipping judge/audit test)")

    n = int(os.getenv("AI_JUDGE_N", "50"))
    seed = int(os.getenv("AI_JUDGE_SEED", "2024"))
    max_failed_audit = int(os.getenv("AI_JUDGE_MAX_FAILED_AUDIT", "5"))

    images = _load_images()
    cases = _generate_profiles(n, seed)

    failures: list[str] = []
    results: list[dict] = []
    failed_audit = 0

    for c in cases:
        img = random.choice(images)
        b64 = _img_to_b64(img)

        user_profile = dict(c["user_profile"])
        user_profile["base64_img"] = b64

        res = get_suggestions(user_profile, c["goal"], client=None)
        if not getattr(res, "success", False) or not getattr(res, "data", None):
            failures.append(f"{c['id']}: AI call failed: {getattr(res, 'error', None)}")
            continue

        data = res.data
        audit = data.get("audit")
        passed = None
        if isinstance(audit, dict):
            passed = audit.get("passed")

        if passed is False:
            failed_audit += 1

        results.append(
            {
                "id": c["id"],
                "image": img.name,
                "chronics": c["user_profile"]["chronics"],
                "allergies": c["user_profile"]["allergies"],
                "mark": _extract_score_mark(data),
                "audit": audit,
            }
        )

    out = _write_run(f"judge_audit_{n}", {"failed_audit": failed_audit, "failures": failures, "results": results})

    assert not failures, f"Judge/audit: some calls failed. Saved: {out}\n" + "\n".join(failures[:20])
    assert failed_audit <= max_failed_audit, (
        f"Too many audit failures ({failed_audit} > {max_failed_audit}). Saved: {out}"
    )