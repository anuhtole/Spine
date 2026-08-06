import datetime as dt

from spine.core.policy_engine import decide, match_policy
from spine.schemas.intercept import AgentAction


def test_default_deny_when_no_match():
    decision, allowed, reason = decide([])
    assert decision == "blocked"
    assert allowed is False
    assert reason == "No matching policy"


def test_allow_match():
    action = AgentAction(action_type="read", target_resource="/patient-records/123")
    m = match_policy("allow", {"effect": "allow", "target_resource_regex": r"^/patient-records/.*"}, action)
    assert m is not None
    decision, allowed, reason = decide([m])
    assert decision == "allowed"
    assert allowed is True
    assert reason == "allow"


def test_deny_overrides_allow():
    action = AgentAction(action_type="read", target_resource="/patient-records/123")
    allow = match_policy("allow", {"effect": "allow"}, action)
    deny = match_policy("deny", {"effect": "deny"}, action)
    assert allow is not None and deny is not None
    decision, allowed, reason = decide([allow, deny])
    assert decision == "blocked"
    assert allowed is False
    assert reason == "deny"


def test_time_window_blocks_outside():
    action = AgentAction(action_type="read", target_resource="/patient-records/123")
    rule = {"effect": "allow", "time_window_utc": {"start": "09:00", "end": "17:00"}}
    nine_am = dt.datetime(2026, 1, 1, 9, 0, tzinfo=dt.timezone.utc)
    eight_pm = dt.datetime(2026, 1, 1, 20, 0, tzinfo=dt.timezone.utc)

    assert match_policy("allow", rule, action, now=nine_am) is not None

    # ensure evaluation respects time when passed through evaluate_policy
    from spine.core.policy_engine import evaluate_policy

    assert evaluate_policy(rule, action, now=nine_am) is True
    assert evaluate_policy(rule, action, now=eight_pm) is False
