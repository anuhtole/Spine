## What this changes

<!-- A sentence or two. What problem does this solve? -->

## How it was verified

<!-- Which of these you ran, and what they said. `make verify` runs all of them. -->

- [ ] `make test` — backend and hook tests
- [ ] `make smoke` — end-to-end
- [ ] `make dashboard-check` — only if the dashboard changed
- [ ] `ruff check .` and `ruff format .`

## Safety invariants

`CLAUDE.md` lists seven invariants that hold the security claims together.
Please confirm this change does not touch them, or explain why it does.

- [ ] The audit hash formula is unchanged, or changed identically in all three
      places (`audit_logger.py`, `sync_audit_logger.py`, `audit_verify.py`)
- [ ] `build_plan_user_message` still accepts only the declared plan and
      minimal structured action fields — no file contents, tool outputs, or
      metadata
- [ ] Default-deny is intact; no global fallback allow was introduced
- [ ] New routes filter by `org_id`
- [ ] No LLM call or blocking external call was added to the intercept path

## Anything else

<!-- Trade-offs, follow-ups, or parts you would like a closer look at. -->
