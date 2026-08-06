from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from spine.schemas.intercept import AgentAction


@dataclass(frozen=True)
class PolicyMatch:
    effect: str  # allow | deny | flag
    reason: str


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _match_action_type(rule_config: dict, action: AgentAction) -> bool:
    allowed_types = rule_config.get("action_types")
    if not allowed_types:
        return True
    return action.action_type in set(allowed_types)


def _match_target_resource(rule_config: dict, action: AgentAction) -> bool:
    pattern = rule_config.get("target_resource_regex")
    if not pattern:
        return True
    if not action.target_resource:
        return False
    return re.search(pattern, action.target_resource) is not None


def _match_time_window(rule_config: dict, now: dt.datetime) -> bool:
    window = rule_config.get("time_window_utc")
    if not window:
        return True

    start = window.get("start")  # "09:00"
    end = window.get("end")  # "17:00"
    if not start or not end:
        return True

    def parse_hhmm(value: str) -> dt.time:
        h, m = value.split(":")
        return dt.time(hour=int(h), minute=int(m), tzinfo=dt.timezone.utc)

    start_t = parse_hhmm(start)
    end_t = parse_hhmm(end)
    now_t = now.timetz()

    if start_t <= end_t:
        return start_t <= now_t <= end_t
    # overnight window (e.g. 22:00-02:00)
    return now_t >= start_t or now_t <= end_t


def evaluate_policy(rule_config: dict, action: AgentAction, *, now: dt.datetime | None = None) -> bool:
    now = now or _now_utc()
    return (
        _match_action_type(rule_config, action)
        and _match_target_resource(rule_config, action)
        and _match_time_window(rule_config, now)
    )


def match_policy(
    name: str, rule_config: dict, action: AgentAction, *, now: dt.datetime | None = None
) -> PolicyMatch | None:
    """
    rule_config format (MVP):
      effect: allow|deny|flag (default: deny)
      action_types: [ ... ] (optional)
      target_resource_regex: "..." (optional)
      time_window_utc: {start: "09:00", end: "17:00"} (optional)
    """
    if not evaluate_policy(rule_config, action, now=now):
        return None

    effect = (rule_config.get("effect") or "deny").lower()
    if effect not in {"allow", "deny", "flag"}:
        effect = "deny"

    return PolicyMatch(effect=effect, reason=name)


def decide(matched: list[PolicyMatch]) -> tuple[str, bool, str]:
    """
    Decision precedence:
      - deny match => blocked
      - else allow match => allowed
      - else flag match => flagged
      - else default => blocked (default-deny)
    """
    if not matched:
        return ("blocked", False, "No matching policy")

    for m in matched:
        if m.effect == "deny":
            return ("blocked", False, m.reason)

    for m in matched:
        if m.effect == "allow":
            return ("allowed", True, m.reason)

    for m in matched:
        if m.effect == "flag":
            return ("flagged", False, m.reason)

    return ("blocked", False, "No matching policy")
