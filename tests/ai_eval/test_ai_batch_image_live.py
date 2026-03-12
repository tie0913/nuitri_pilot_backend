import base64
import csv
import json
import os
import random
import asyncio
import time
from datetime import datetime
from html import escape
from pathlib import Path

import pytest

from src.suggestion.agent import get_agent
from src.ai.audit import run_ai_audit


IMAGES_DIR = Path(__file__).resolve().parent / "images"
RUNS_DIR = Path(__file__).resolve().parent / "runs"


def _load_images() -> list[Path]:
    assert IMAGES_DIR.exists(), f"Missing images dir: {IMAGES_DIR}"
    imgs: list[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        imgs.extend(IMAGES_DIR.glob(ext))

    # Avoid huge files (helps avoid 400 + timeouts)
    max_bytes = int(os.getenv("AI_MAX_IMAGE_BYTES", "1000000"))
    imgs = [p for p in imgs if p.stat().st_size <= max_bytes]

    assert imgs, f"No usable images found in {IMAGES_DIR} (add jpg/png/webp <= AI_MAX_IMAGE_BYTES)"
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
    _write_case_csv(out, payload)
    _write_case_html(out, payload)
    return out


def _collect_case_rows(payload: dict) -> list[dict]:
    rows: list[dict] = []
    unreadable_phrase = "i could not read the full ingredient list clearly"

    results = payload.get("results", [])
    if not isinstance(results, list):
        return rows

    for i, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue

        normalized = item.get("normalized")
        if not isinstance(normalized, dict):
            normalized = {}
        raw = item.get("raw")
        if not isinstance(raw, dict):
            raw = {}

        recs = _norm_list(normalized.get("recommendation", raw.get("recommendation", [])))
        feedback = str(normalized.get("feedback", raw.get("feedback", "")) or "").strip()
        audit = normalized.get("audit", raw.get("audit"))
        if not isinstance(audit, dict):
            audit = {}
        audit_passed = audit.get("passed", "")
        audit_issues = audit.get("issues", [])
        if not isinstance(audit_issues, list):
            audit_issues = []
        issue_codes = []
        fact_issue_count = 0
        for issue in audit_issues:
            if not isinstance(issue, dict):
                continue
            code = str(issue.get("code", "") or "").strip().upper()
            if not code:
                continue
            issue_codes.append(code)
            if code == "FACT":
                fact_issue_count += 1

        code = normalized.get("code", raw.get("code", ""))
        mark = normalized.get("mark", raw.get("mark", ""))
        ai_score = normalized.get("score", raw.get("score", mark))
        latency = item.get("latency_s", "")

        rows.append(
            {
                "idx": i,
                "id": item.get("id", ""),
                "image": item.get("image", ""),
                "chronics": " | ".join(_norm_list(item.get("chronics", []))),
                "allergies": " | ".join(_norm_list(item.get("allergies", []))),
                "ok": item.get("ok", True),
                "code": code,
                "mark": mark,
                "ai_score": ai_score,
                "latency_s": latency,
                "recommendation_count": len(recs),
                "recommendation": " | ".join(recs),
                "feedback": feedback,
                "audit_passed": audit_passed,
                "audit_issue_codes": " | ".join(issue_codes),
                "fact_issue_count": fact_issue_count,
                "unreadable_feedback": unreadable_phrase in feedback.lower(),
                "error": item.get("error", ""),
            }
        )

    return rows


def _write_case_csv(json_path: Path, payload: dict) -> Path:
    csv_path = json_path.with_suffix(".csv")
    rows = _collect_case_rows(payload)
    fields = [
        "idx",
        "id",
        "image",
        "chronics",
        "allergies",
        "ok",
        "code",
        "mark",
        "ai_score",
        "latency_s",
        "recommendation_count",
        "recommendation",
        "feedback",
        "audit_passed",
        "audit_issue_codes",
        "fact_issue_count",
        "unreadable_feedback",
        "error",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return csv_path


def _write_case_html(json_path: Path, payload: dict) -> Path:
    html_path = json_path.with_suffix(".html")
    rows = _collect_case_rows(payload)
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
    failures = payload.get("failures", []) if isinstance(payload, dict) else []

    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(failures, list):
        failures = []

    n = metrics.get("n", len(rows))
    success_calls = metrics.get("success_calls", "n/a")
    expected_fail_calls = metrics.get("expected_fail_calls", "n/a")
    fail_calls = metrics.get("fail_calls", "n/a")
    timeout_calls = metrics.get("timeout_calls", "n/a")
    success_rate = metrics.get("success_rate", None)
    success_rate_txt = f"{float(success_rate) * 100:.2f}%" if isinstance(success_rate, (float, int)) else "n/a"
    scored_count = summary.get("scored_with_feedback_count", metrics.get("scored_with_feedback_count", "n/a"))
    unreadable_count = summary.get("unreadable_feedback_count", metrics.get("unreadable_feedback_count", "n/a"))
    audit_passed_calls = metrics.get("audit_passed_calls", "n/a")
    audit_failed_calls = metrics.get("audit_failed_calls", "n/a")
    fact_issue_total = metrics.get("fact_issue_total", "n/a")
    issue_counts = summary.get("audit_issue_counts", {})
    if not isinstance(issue_counts, dict):
        issue_counts = {}
    next_actions = summary.get("next_actions", [])
    if not isinstance(next_actions, list):
        next_actions = []

    table_rows: list[str] = []
    for r in rows:
        row_class = ""
        if not r.get("ok", True):
            row_class = ' class="bad"'
        elif r.get("audit_passed") is False:
            row_class = ' class="bad"'
        elif r.get("unreadable_feedback"):
            row_class = ' class="warn"'

        table_rows.append(
            "<tr"
            + row_class
            + ">"
            + f"<td>{escape(str(r.get('idx', '')))}</td>"
            + f"<td>{escape(str(r.get('id', '')))}</td>"
            + f"<td>{escape(str(r.get('image', '')))}</td>"
            + f"<td>{escape(str(r.get('chronics', '')))}</td>"
            + f"<td>{escape(str(r.get('allergies', '')))}</td>"
            + f"<td>{escape(str(r.get('ok', '')))}</td>"
            + f"<td>{escape(str(r.get('code', '')))}</td>"
            + f"<td>{escape(str(r.get('mark', '')))}</td>"
            + f"<td>{escape(str(r.get('ai_score', '')))}</td>"
            + f"<td>{escape(str(r.get('latency_s', '')))}</td>"
            + f"<td>{escape(str(r.get('recommendation_count', '')))}</td>"
            + f"<td>{escape(str(r.get('feedback', '')))}</td>"
            + f"<td>{escape(str(r.get('audit_passed', '')))}</td>"
            + f"<td>{escape(str(r.get('audit_issue_codes', '')))}</td>"
            + f"<td>{escape(str(r.get('fact_issue_count', '')))}</td>"
            + f"<td>{escape(str(r.get('error', '')))}</td>"
            + "</tr>"
        )

    failure_items = "".join(f"<li>{escape(str(x))}</li>" for x in failures) or "<li>None</li>"
    issue_items = "".join(
        f"<li><strong>{escape(str(k))}</strong>: {escape(str(v))}</li>"
        for k, v in sorted(issue_counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))
    ) or "<li>None</li>"
    action_items = "".join(f"<li>{escape(str(x))}</li>" for x in next_actions) or "<li>None</li>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NutriPilot AI Batch Report</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1, h2 {{ margin: 0 0 12px 0; }}
    .meta {{ color: #4b5563; margin-bottom: 20px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0 20px; }}
    .kpi {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; background: #f9fafb; }}
    .kpi .label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.04em; }}
    .kpi .value {{ font-size: 22px; font-weight: 700; margin-top: 6px; }}
    .panel {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; vertical-align: top; word-wrap: break-word; font-size: 12px; }}
    th {{ background: #f3f4f6; text-align: left; }}
    tr.warn {{ background: #fffbeb; }}
    tr.bad {{ background: #fef2f2; }}
    .small {{ font-size: 12px; color: #6b7280; }}
  </style>
</head>
<body>
  <h1>NutriPilot AI Image Batch Report</h1>
  <div class="meta">Generated: {escape(datetime.now().isoformat())} | Source: {escape(str(json_path.name))}</div>

    <div class="kpis">
      <div class="kpi"><div class="label">Total Cases</div><div class="value">{escape(str(n))}</div></div>
      <div class="kpi"><div class="label">Scored (code=0, mark&gt;0)</div><div class="value">{escape(str(scored_count))}</div></div>
      <div class="kpi"><div class="label">Unreadable Feedback</div><div class="value">{escape(str(unreadable_count))}</div></div>
      <div class="kpi"><div class="label">Audit Passed</div><div class="value">{escape(str(audit_passed_calls))}</div></div>
      <div class="kpi"><div class="label">Audit Failed</div><div class="value">{escape(str(audit_failed_calls))}</div></div>
      <div class="kpi"><div class="label">FACT Issues</div><div class="value">{escape(str(fact_issue_total))}</div></div>
      <div class="kpi"><div class="label">Success Calls</div><div class="value">{escape(str(success_calls))}</div></div>
      <div class="kpi"><div class="label">Expected Fail Calls</div><div class="value">{escape(str(expected_fail_calls))}</div></div>
      <div class="kpi"><div class="label">Call Exceptions</div><div class="value">{escape(str(fail_calls))}</div></div>
      <div class="kpi"><div class="label">Timeout Calls</div><div class="value">{escape(str(timeout_calls))}</div></div>
      <div class="kpi"><div class="label">Success Rate</div><div class="value">{escape(success_rate_txt)}</div></div>
  </div>

  <div class="panel">
    <h2>Failure Summary</h2>
    <ul>{failure_items}</ul>
  </div>

  <div class="panel">
    <h2>Audit Issue Breakdown</h2>
    <ul>{issue_items}</ul>
  </div>

  <div class="panel">
    <h2>What To Do Next</h2>
    <ul>{action_items}</ul>
  </div>

  <div class="panel">
    <h2>Case-Level Results</h2>
    <div class="small">Rows in yellow are unreadable-label feedback. Rows in red are call-level exceptions.</div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Case ID</th>
          <th>Image</th>
          <th>Chronics</th>
          <th>Allergies</th>
          <th>OK</th>
          <th>Code</th>
          <th>Mark</th>
          <th>AI Score</th>
          <th>Latency(s)</th>
          <th>Recs</th>
          <th>Feedback</th>
          <th>Audit Passed</th>
          <th>Issue Codes</th>
          <th>FACT Count</th>
          <th>Error</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    html_path.write_text(html, encoding="utf-8")
    return html_path


def _generate_profiles(n: int, seed: int) -> list[dict]:
    random.seed(seed)

    chronic_candidates = ["pcos", "thyroid", "prediabetes", "hypertension"]
    allergy_candidates = ["peanut", "lactose", "gluten", "soy"]

    def _resolve_max(env_name: str, pool_size: int) -> int:
        raw = str(os.getenv(env_name, "")).strip()
        if not raw:
            # Default: allow full pool so cases can contain many profile items.
            return pool_size
        try:
            value = int(raw)
        except ValueError:
            return pool_size
        return max(0, min(pool_size, value))

    max_chronics = _resolve_max("AI_MAX_CHRONICS_PER_CASE", len(chronic_candidates))
    max_allergies = _resolve_max("AI_MAX_ALLERGIES_PER_CASE", len(allergy_candidates))

    def _pick_many(pool: list[str], max_items: int) -> list[str]:
        if max_items <= 0:
            return []
        count = random.randint(0, max_items)
        if count == 0:
            return []
        return random.sample(pool, count)

    return [
        {
            "id": f"case_{i:03d}",
            "chronics": _pick_many(chronic_candidates, max_chronics),
            "allergies": _pick_many(allergy_candidates, max_allergies),
        }
        for i in range(1, n + 1)
    ]


def _next_actions(
    issue_counts: dict[str, int],
    unreadable_feedback_count: int,
    fail_calls: int,
    timeout_calls: int,
) -> list[str]:
    actions: list[str] = []
    if issue_counts.get("FACT", 0) > 0:
        actions.append(
            "Reduce unsupported claims: feedback should cite detected ingredients/nutrition, or state uncertainty clearly."
        )
    if unreadable_feedback_count > 0:
        actions.append(
            "Improve label readability outcomes: request close-up ingredient photos and improve image preprocessing."
        )
    if fail_calls > 0:
        actions.append(
            "Call exceptions found: reduce image size, validate model config, and retry with lower concurrency."
        )
    if timeout_calls > 0:
        actions.append(
            "Timeouts detected: increase AI_PER_CALL_TIMEOUT or lower AI_CONCURRENCY."
        )
    if not actions:
        actions.append("No major issues detected. Expand edge-case coverage and keep baseline snapshots updated.")
    return actions


async def _agent_call(base64_img: str, chronics: list[str], allergies: list[str]) -> dict:
    agent = get_agent()
    return await agent.get(base64_img, chronics, allergies)


@pytest.mark.ai_live
@pytest.mark.ai_batch
@pytest.mark.ai_image
@pytest.mark.asyncio
async def test_ai_image_batch_100_live():
    """
    IMAGE pipeline batch test:
    Calls agent.get(base64_img, chronics, allergies) N times.

    Accepts TWO valid outcomes:
    1) code == 0 (success): ingredient list read + scored
    2) code == 1 (expected failure): unreadable image, but must return stable schema

    Also enforces QUALITY:
    - success_rate >= AI_MIN_SUCCESS_RATE (default 0.6)

    Also logs PERFORMANCE:
    - avg_latency_s, p50_latency_s, p95_latency_s, timeout_calls
    """
    n = int(os.getenv("AI_BATCH_N", "100"))
    seed = int(os.getenv("AI_BATCH_SEED", "12345"))
    max_fail = int(os.getenv("AI_BATCH_MAX_FAILURES", "10"))

    # Tunables
    min_mark = float(os.getenv("AI_MIN_MARK", "1"))  # applies ONLY when code==0
    min_recs = int(os.getenv("AI_MIN_RECS", "3"))
    max_recs = int(os.getenv("AI_MAX_RECS", "12"))
    min_feedback_words = int(os.getenv("AI_MIN_FEEDBACK_WORDS", "20"))

    # Runtime controls
    per_call_timeout = float(os.getenv("AI_PER_CALL_TIMEOUT", "45"))
    concurrency = int(os.getenv("AI_CONCURRENCY", "5"))
    if concurrency < 1:
        concurrency = 1

    # Quality gates
    min_success_rate = float(os.getenv("AI_MIN_SUCCESS_RATE", "0.6"))
    max_p95_latency_s = float(os.getenv("AI_MAX_P95_LATENCY_S", "0"))  # 0 disables gate
    max_failed_audit = int(os.getenv("AI_MAX_FAILED_AUDIT", "-1"))  # -1 disables gate
    diagnostic_mode = os.getenv("AI_DIAGNOSTIC_MODE", "0") == "1"

    images = _load_images()
    cases = _generate_profiles(n, seed)

    failures: list[str] = []
    results: list[dict] = []

    # Metrics
    fail_calls = 0  # agent call crashed / returned non-dict
    timeout_calls = 0  # how many calls hit asyncio timeout
    success_calls = 0  # code == 0
    expected_fail_calls = 0  # code == 1
    audit_passed_calls = 0
    audit_failed_calls = 0
    fact_issue_total = 0
    latencies_s: list[float] = []

    sem = asyncio.Semaphore(concurrency)
    fail_lock = asyncio.Lock()  # protect fail_calls / failures / early-stop checks

    async def _run_one(c: dict) -> None:
        nonlocal fail_calls, timeout_calls, success_calls, expected_fail_calls
        nonlocal audit_passed_calls, audit_failed_calls, fact_issue_total

        img = random.choice(images)
        b64 = _img_to_b64(img)

        # -------------------------
        # Call agent (bounded + concurrency-controlled)
        # -------------------------
        t0 = time.perf_counter()
        suggestion = None
        ok = False
        err = None

        async with sem:
            try:
                suggestion = await asyncio.wait_for(
                    _agent_call(b64, c["chronics"], c["allergies"]),
                    timeout=per_call_timeout,
                )
                ok = isinstance(suggestion, dict)
            except asyncio.TimeoutError:
                timeout_calls += 1
                err = f"TimeoutError: exceeded {per_call_timeout}s"
            except Exception as e:
                err = f"{type(e).__name__}: {e}"

        dt = time.perf_counter() - t0
        latencies_s.append(dt)

        if not ok:
            async with fail_lock:
                fail_calls += 1
                failures.append(f"{c['id']}: agent call exception: {err}")
                results.append(
                    {
                        "id": c["id"],
                        "image": img.name,
                        "chronics": c["chronics"],
                        "allergies": c["allergies"],
                        "ok": False,
                        "latency_s": round(dt, 4),
                        "raw": suggestion,
                        "error": err,
                    }
                )

                # Early-stop: too many call-level failures
                if fail_calls > max_fail:
                    out = _write_run(
                        f"image_batch_{n}_EARLY_STOP",
                        {
                            "failures": failures,
                            "results": results,
                            "metrics": {
                                "n": n,
                                "concurrency": concurrency,
                                "per_call_timeout_s": per_call_timeout,
                                "fail_calls": fail_calls,
                                "timeout_calls": timeout_calls,
                                "success_calls": success_calls,
                                "expected_fail_calls": expected_fail_calls,
                                "avg_latency_s": (sum(latencies_s) / len(latencies_s)) if latencies_s else None,
                            },
                        },
                    )
                    pytest.fail(f"Too many image AI call failures (> {max_fail}). Saved: {out}")
            return

        # -------------------------
        # Validate normalized schema
        # -------------------------
        code = suggestion.get("code")
        msg = str(suggestion.get("message", "") or "")
        recs = _norm_list(suggestion.get("recommendation"))
        mark = suggestion.get("mark")
        audit = suggestion.get("audit")
        feedback = str(suggestion.get("feedback", "") or "")
        detected = suggestion.get("detected_ingredients", suggestion.get("ingredients", []))

        # code must be 0 or 1
        try:
            code_int = int(code)
        except Exception:
            code_int = -999
        if code_int not in (0, 1):
            failures.append(f"{c['id']}: invalid code (expected 0/1, got {code})")

        # message should NOT leak SDK exception names
        if "BadRequestError" in msg:
            failures.append(f"{c['id']}: BadRequestError leaked in message: {msg}")

        # recommendation sanity (both success + expected failure)
        if len(recs) < min_recs:
            failures.append(f"{c['id']}: recommendation too short (got {len(recs)})")
        if len(recs) > max_recs:
            failures.append(f"{c['id']}: recommendation too long (got {len(recs)})")

        # feedback sanity (both)
        if len(feedback.split()) < min_feedback_words:
            failures.append(
                f"{c['id']}: feedback too short (got {len(feedback.split())} words, need >= {min_feedback_words})"
            )

        # detected_ingredients should be list-like (both)
        if detected is None:
            detected = []
        if not isinstance(detected, list):
            failures.append(f"{c['id']}: detected_ingredients must be a list (got {type(detected).__name__})")
            detected = []
        detected = [str(x).strip() for x in detected if str(x).strip()]

        # Deterministic audit check so batch report can show factual/truth issues.
        audit_result = run_ai_audit(
            ai_output={
                "code": code_int if code_int in (0, 1) else suggestion.get("code"),
                "message": msg,
                "mark": mark,
                "level": suggestion.get("level", 2),
                "feedback": feedback,
                "recommendation": recs,
                "detected_ingredients": detected,
            },
            user_allergies=[str(x).strip() for x in (c.get("allergies") or []) if str(x).strip()],
            detected_ingredients=detected,
            nutrition=None,
        )
        audit = {
            "passed": audit_result.passed,
            "issues": audit_result.issues,
            "judge_notes": audit_result.judge_notes,
        }
        if audit_result.passed:
            audit_passed_calls += 1
        else:
            audit_failed_calls += 1
        for issue in (audit_result.issues or []):
            if isinstance(issue, dict) and str(issue.get("code", "")).upper() == "FACT":
                fact_issue_total += 1

        # -------------------------
        # Branch: expected failure vs success
        # -------------------------
        if code_int == 1:
            expected_fail_calls += 1

            # For expected failures, mark must be 0
            try:
                m = float(mark or 0)
            except Exception:
                m = None
            if m is None:
                failures.append(f"{c['id']}: code=1 but mark not numeric (got {mark})")
            else:
                if m != 0.0:
                    failures.append(f"{c['id']}: code=1 but mark must be 0 (got {m})")

            results.append(
                {
                    "id": c["id"],
                    "image": img.name,
                    "chronics": c["chronics"],
                    "allergies": c["allergies"],
                    "ok": True,
                    "latency_s": round(dt, 4),
                    "normalized": {
                        "recommendation": recs,
                        "mark": mark,
                        "code": code_int,
                        "message": msg,
                        "audit": audit,
                        "feedback": feedback,
                    },
                    "raw": suggestion,
                }
            )
            return

        # code_int == 0 success validations:
        success_calls += 1

        # mark must be 0..100 and >= min_mark
        if mark is None:
            failures.append(f"{c['id']}: missing mark")
        else:
            try:
                m = float(mark)
                if not (0.0 <= m <= 100.0):
                    failures.append(f"{c['id']}: mark out of range 0-100 (got {m})")
                if m < min_mark:
                    failures.append(f"{c['id']}: mark below min threshold {min_mark} (got {m})")
            except Exception:
                failures.append(f"{c['id']}: mark not numeric (got {mark})")

        # Optional audit shape check (if present)
        if audit is not None and isinstance(audit, dict) and "passed" not in audit:
            failures.append(f"{c['id']}: audit present but missing 'passed'")

        results.append(
            {
                "id": c["id"],
                "image": img.name,
                "chronics": c["chronics"],
                "allergies": c["allergies"],
                "ok": True,
                "latency_s": round(dt, 4),
                "normalized": {
                    "recommendation": recs,
                    "mark": mark,
                    "code": code_int,
                    "message": msg,
                    "audit": audit,
                    "feedback": feedback,
                },
                "raw": suggestion,
            }
        )

    # Run all cases with bounded concurrency
    await asyncio.gather(*(_run_one(c) for c in cases))

    # Metrics summary
    avg_latency = (sum(latencies_s) / len(latencies_s)) if latencies_s else None
    lat_sorted = sorted(latencies_s)
    p50 = lat_sorted[int(0.50 * (len(lat_sorted) - 1))] if lat_sorted else None
    p95 = lat_sorted[int(0.95 * (len(lat_sorted) - 1))] if lat_sorted else None

    total_returned = success_calls + expected_fail_calls
    success_rate = (success_calls / total_returned) if total_returned else 0.0
    expected_fail_rate = (expected_fail_calls / total_returned) if total_returned else 0.0

    # End-of-run readability summary requested by product team:
    # - how many had a real scored feedback (code=0 and mark>0)
    # - how many returned "could not read ingredient list clearly" feedback
    unreadable_phrase = "i could not read the full ingredient list clearly"
    scored_with_feedback: list[dict] = []
    unreadable_feedback_cases: list[dict] = []

    for item in results:
        if not item.get("ok"):
            continue
        normalized = item.get("normalized") or {}

        feedback_txt = str(normalized.get("feedback", "") or "").strip()
        mark_val = normalized.get("mark")
        code_val = normalized.get("code")

        try:
            code_int = int(code_val)
        except Exception:
            code_int = -999

        mark_float = None
        try:
            mark_float = float(mark_val)
        except Exception:
            pass

        if code_int == 0 and mark_float is not None and mark_float > 0:
            scored_with_feedback.append(
                {
                    "id": item.get("id"),
                    "image": item.get("image"),
                    "mark": mark_float,
                    "feedback": feedback_txt,
                }
            )

        if unreadable_phrase in feedback_txt.lower():
            unreadable_feedback_cases.append(
                {
                    "id": item.get("id"),
                    "image": item.get("image"),
                    "mark": mark_val,
                    "code": code_val,
                    "feedback": feedback_txt,
                }
            )

    scored_with_feedback_count = len(scored_with_feedback)
    unreadable_feedback_count = len(unreadable_feedback_cases)
    audit_issue_counts: dict[str, int] = {}
    for item in results:
        normalized = item.get("normalized", {}) if isinstance(item, dict) else {}
        audit_obj = normalized.get("audit") if isinstance(normalized, dict) else None
        if not isinstance(audit_obj, dict):
            continue
        issues = audit_obj.get("issues", [])
        if not isinstance(issues, list):
            continue
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            code_name = str(issue.get("code", "UNKNOWN") or "UNKNOWN").upper()
            audit_issue_counts[code_name] = audit_issue_counts.get(code_name, 0) + 1
    next_actions = _next_actions(audit_issue_counts, unreadable_feedback_count, fail_calls, timeout_calls)

    # Quality gate
    if total_returned > 0 and success_rate < min_success_rate:
        failures.append(
            f"success_rate too low: {success_calls}/{total_returned} = {success_rate:.2%} "
            f"(need >= {min_success_rate:.0%})"
        )

    # Optional latency gate (disabled by default)
    if max_p95_latency_s > 0 and p95 is not None and p95 > max_p95_latency_s:
        failures.append(f"p95 latency too high: {p95:.2f}s (need <= {max_p95_latency_s:.2f}s)")
    if max_failed_audit >= 0 and audit_failed_calls > max_failed_audit:
        failures.append(f"audit_failed_calls too high: {audit_failed_calls} > {max_failed_audit}")

    gate_prefixes = (
        "success_rate too low:",
        "p95 latency too high:",
        "audit_failed_calls too high:",
    )
    gate_failures = [f for f in failures if isinstance(f, str) and f.startswith(gate_prefixes)]
    if diagnostic_mode:
        # Keep signal in report but don't fail run on high-level quality gates.
        failures = [f for f in failures if not (isinstance(f, str) and f.startswith(gate_prefixes))]
        if gate_failures:
            next_actions.append(
                "Diagnostic mode is ON: quality gate failures were recorded but did not fail the run."
            )

    # Call-level exceptions are tolerated up to AI_BATCH_MAX_FAILURES.
    call_exception_token = ": agent call exception:"
    call_exception_failures = [
        f for f in failures if isinstance(f, str) and call_exception_token in f
    ]
    blocking_failures = failures
    tolerated_call_failures = 0
    if fail_calls <= max_fail:
        blocking_failures = [
            f for f in failures if not (isinstance(f, str) and call_exception_token in f)
        ]
        tolerated_call_failures = len(call_exception_failures)
        if tolerated_call_failures > 0:
            next_actions.append(
                f"Tolerated {tolerated_call_failures} call exception(s) within AI_BATCH_MAX_FAILURES={max_fail}. "
                "Tune timeout/concurrency to reduce flakiness."
            )

    out = _write_run(
        f"image_batch_{n}",
        {
            "failures": failures,
            "blocking_failures": blocking_failures,
            "results": results,
            "summary": {
                "scored_with_feedback_count": scored_with_feedback_count,
                "unreadable_feedback_count": unreadable_feedback_count,
                "scored_with_feedback_samples": scored_with_feedback[:20],
                "unreadable_feedback_samples": unreadable_feedback_cases[:20],
                "audit_issue_counts": audit_issue_counts,
                "next_actions": next_actions,
                "gate_failures": gate_failures,
                "tolerated_call_failures": tolerated_call_failures,
            },
            "metrics": {
                "n": n,
                "concurrency": concurrency,
                "per_call_timeout_s": per_call_timeout,
                "fail_calls": fail_calls,
                "timeout_calls": timeout_calls,
                "success_calls": success_calls,
                "expected_fail_calls": expected_fail_calls,
                "audit_passed_calls": audit_passed_calls,
                "audit_failed_calls": audit_failed_calls,
                "fact_issue_total": fact_issue_total,
                "total_returned": total_returned,
                "success_rate": success_rate,
                "expected_fail_rate": expected_fail_rate,
                "scored_with_feedback_count": scored_with_feedback_count,
                "unreadable_feedback_count": unreadable_feedback_count,
                "avg_latency_s": avg_latency,
                "p50_latency_s": p50,
                "p95_latency_s": p95,
                "min_success_rate": min_success_rate,
                "max_p95_latency_s": (max_p95_latency_s if max_p95_latency_s > 0 else None),
                "max_failed_audit": (max_failed_audit if max_failed_audit >= 0 else None),
                "diagnostic_mode": diagnostic_mode,
                "tolerated_call_failures": tolerated_call_failures,
                "blocking_failures_count": len(blocking_failures),
            },
        },
    )
    assert not blocking_failures, (
        f"Image batch blocking failures ({len(blocking_failures)}). Saved: {out}\n"
        f"Scored with mark>0: {scored_with_feedback_count} | "
        f"Unreadable-feedback count: {unreadable_feedback_count} | "
        f"Tolerated call failures: {tolerated_call_failures}\n"
        + "\n".join(blocking_failures[:50])
    )
