---
description: Create a review task doc and route review work through installed Superpowers skills.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title] [goal]
---

1. Confirm Superpowers is installed and enabled in Claude. If not, stop and tell the user to install/enable the plugin first.
2. Run `python3 .so2x-system/scripts/execute.py flow-review --title "<title>" --goal "<goal>"` using the user request.
3. Read `run_output` and follow `gate_results` first. If blocked, stop and report the blocker.
4. If any `dispatch_results` entry is `failed`, stop and report the exact runner/plugin configuration error.
5. If any `dispatch_results` entry is `simulated`, explicitly report that no real dispatch happened yet and that plugin enablement or `SO2X_SYSTEM_SUPERPOWER_COMMAND` is still required.
6. Only for real runnable steps should you follow `dispatch_plan` and execute each `superpowers:*` target in order.
7. Use `dispatch_results` as the recorded execution/result surface from so2x-system.

Default title: `Review task`.
