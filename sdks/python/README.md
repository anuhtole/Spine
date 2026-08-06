# Spine Python SDK (thin client)

This is intentionally small: it standardizes how your agent code calls the Spine control plane.

## Install (local path)

```bash
pip install -e ./sdks/python
```

## Usage

```python
import httpx
from spine_sdk import SpineClient

client = SpineClient(
    base_url="http://127.0.0.1:8000",
    org_key="spine_...",
    http_client=httpx.Client(),
)
result = client.intercept(agent_id=..., action_type="read", target_resource="/x")
if not result.json.get("allowed"):
    raise RuntimeError(result.json)
```

## Block before tools run

```python
from spine_sdk import SpineClient, require_allowed, guard_tool

require_allowed(client, agent_id=aid, action_type="read", target_resource="/path/to/file")

# Or decorate a tool (see examples/langgraph_tool.py)
```

## Claude Code

For Claude Code integration, use the drop-in `PreToolUse` hook in
[`integrations/claude-code-spine/`](../../integrations/claude-code-spine/)
— `./install.sh` and you're done. The hook is independent of this SDK
and uses only the Python standard library.
