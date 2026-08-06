from __future__ import annotations

from prometheus_client import Counter, Histogram

spine_intercepts_total = Counter(
    "spine_intercepts_total",
    "Total intercept decisions",
    labelnames=("decision", "allowed"),
)

# ── Latency histograms (Phase A) ──────────────────────────────────────────
# Buckets tuned for the synchronous intercept hot path: sub-50ms is the goal.
spine_intercept_duration_seconds = Histogram(
    "spine_intercept_duration_seconds",
    "Wall-clock latency of POST /v1/intercept",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Plan evaluations are async (worker) — order of seconds, not ms.
spine_plan_eval_duration_seconds = Histogram(
    "spine_plan_eval_duration_seconds",
    "Wall-clock latency of one plan_alignment evaluation",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0),
)

# Policy cache observability
spine_policy_cache_events_total = Counter(
    "spine_policy_cache_events_total",
    "Policy cache lookups by outcome",
    labelnames=("outcome",),
)


def inc_policy_cache_event(outcome: str) -> None:
    """outcome ∈ {hit, miss, error, bypass}"""
    spine_policy_cache_events_total.labels(outcome=str(outcome)).inc()


# Plan-bound reviewer records each verdict here (recommendation = alignment,
# monitor_type = "plan_alignment"). This is the reviewer's own metric.
spine_monitor_evaluations_total = Counter(
    "spine_monitor_evaluations_total",
    "Total plan-alignment evaluations",
    labelnames=("recommendation", "monitor_type"),
)


def inc_intercept(*, decision: str, allowed: bool) -> None:
    spine_intercepts_total.labels(decision=str(decision), allowed="true" if allowed else "false").inc()


def inc_monitor_evaluation(*, recommendation: str, monitor_type: str = "plan_alignment") -> None:
    spine_monitor_evaluations_total.labels(recommendation=str(recommendation), monitor_type=str(monitor_type)).inc()
