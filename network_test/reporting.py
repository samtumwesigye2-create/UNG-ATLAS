"""Reporting and readiness scoring for ATLAS network tests."""
from __future__ import annotations

from collections import Counter
from .models import EventResult
from .runner import summarize


def readiness_score(results: list[EventResult]) -> dict:
    base = summarize(results)
    success = base["success_rate"] * 100
    retry_penalty = min(15.0, sum(r.retries for r in results) / max(1, len(results)) * 10)
    consistency_failures = sum(r.consistency_ok is False for r in results)
    recovery_failures = sum(r.recovery_ok is False for r in results)
    consistency_penalty = min(20.0, consistency_failures / max(1, len(results)) * 100)
    recovery_penalty = min(15.0, recovery_failures / max(1, len(results)) * 100)
    score = max(0.0, min(100.0, success - retry_penalty - consistency_penalty - recovery_penalty))
    grade = "READY" if score >= 95 else "CONDITIONAL" if score >= 80 else "NOT_READY"
    return {"score": round(score, 2), "grade": grade, "penalties": {
        "retry": round(retry_penalty, 2), "consistency": round(consistency_penalty, 2), "recovery": round(recovery_penalty, 2)}}


def build_report(batch_results: list[list[EventResult]], run_id: str) -> dict:
    all_results = [r for batch in batch_results for r in batch]
    failures = Counter((r.destination_system or "UNROUTED", r.failure_reason or "unknown") for r in all_results if r.status != "accepted")
    return {
        "run_id": run_id,
        "batches": [{"batch": i + 1, **summarize(rows)} for i, rows in enumerate(batch_results)],
        "overall": summarize(all_results),
        "readiness": readiness_score(all_results),
        "top_failures": [
            {"system": system, "reason": reason, "count": count}
            for (system, reason), count in failures.most_common(20)
        ],
        "controls": {"test_mode_required": True, "synthetic_required": True, "batch_limit": 3000, "batch_count": 4},
    }
