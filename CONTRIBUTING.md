# Contributing

Thanks for looking. Issues and pull requests are welcome.

## Getting set up

```bash
git clone https://github.com/VishnuR23/spine.git
cd spine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
make demo          # brings up the stack and seeds a working demo
```

Python 3.12+, Node 20+, Docker.

## Before you open a pull request

```bash
make verify
```

That runs all four gates: backend tests, Claude Code hook tests, the
end-to-end smoke test, and the dashboard typecheck and build. CI runs the
same thing. The smoke test is the one that catches real breakage — it boots
a server, runs a full session lifecycle, and drives the hook as a subprocess.

Also run `ruff check .` and `ruff format .`.

## What makes a change easy to merge

**Read [CLAUDE.md](CLAUDE.md) first.** It is written for AI assistants but it
is the actual operating manual: seven safety invariants, the caching rules,
the hot-path latency budget, and a list of bugs this project has already had.
A change that violates an invariant will not be merged, and the file explains
why each one exists.

The two that catch people out:

1. **The audit hash formula lives in three files** — `audit_logger.py`,
   `sync_audit_logger.py`, `audit_verify.py` — and they must agree exactly.
   Adding a field to the hash means adding it identically in all three, gated
   on non-null so historical rows still verify.

2. **The plan reviewer's input builder must stay narrow.**
   `build_plan_user_message` accepts only the declared plan and minimal
   structured action fields. Widening it to accept file contents, tool
   outputs, or metadata defeats the entire design.
   `tests/test_plan_prompt_isolation.py` guards this.

Beyond that: tests for new behavior, a docs update if you changed the API,
and `make openapi` if you changed a route.

## Good first contributions

- **Policy expressiveness.** The rule language is action type, target regex,
  and time window. Resource hierarchies, rate-based rules, and argument
  matching are all reasonable additions.
- **Framework integrations.** There is a Claude Code hook and two thin SDKs.
  LangChain, CrewAI, AutoGen, and MCP servers are all unserved.
- **Adversarial testing of the reviewer.** If you can get agent-controlled
  content into the reviewer's input, that is the most valuable bug you could
  file. Start with `examples/injection_isolation.py`.
- **Docs.** If something took you longer to figure out than it should have,
  that is a bug in the docs.

## Scope

Spine tries to be two things well: a fast deterministic gate, and a reviewer
that cannot be talked out of its judgment. Proposals that add a third layer
are a harder sell than proposals that make either of those two better.

## Security issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

## License

Contributions are accepted under the Apache License 2.0, the same license
that covers the project.
