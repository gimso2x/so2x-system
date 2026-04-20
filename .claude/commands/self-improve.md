---
description: Scan recent so2x-system signals, write candidate rules/skills, and sync approved rules into future runs.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title]
---

1. Run `python3 .so2x-system/scripts/execute.py self-improve --title "<title>"`.
2. Read `run_output`; `dispatch_plan` should contain only local `internal` steps and `gate_results` should remain informational.
3. Review the generated candidate files.
4. If a candidate is human-approved, mark `approved: true` in that candidate file so future runs load it automatically.

Default title: `Promote repeated patterns`.
