---
description: Start a Spine plan-bound session for the current task.
argument-hint: <free-form description of what you're trying to do>
allowed-tools: Bash(python3:*)
---

Register a Spine plan-bound session for this task. The reviewer will compare
every subsequent tool call against the goal you state here.

Run this in your current project directory:

```bash
python3 ~/.spine/spine-session-cli.py start "$ARGUMENTS"
```

The session ID is saved to `.spine/session_id` in your current project and is
automatically attached to every following Spine intercept by the hook.

When you're done with the task, run `/spine-session-end` to close the session
and see the final drift score.
