---
description: Create a QA task doc and route debugging work through installed Superpowers skills.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title] [goal]
---

1. Confirm Superpowers is installed in Claude. If not, stop and tell the user to install the plugin first.
2. Run `python3 .so2x-system/scripts/execute.py flow-qa --title "<title>" --goal "<goal>"` using the user request.
3. Read `run_output` and follow `gate_results` first. If blocked, stop and report the blocker.
4. Then follow `dispatch_plan` and execute each `superpowers:*` target in order.
5. Use `dispatch_results` as the recorded execution/result surface from so2x-system.

Default title: `QA task`.
