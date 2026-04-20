---
description: Create or refresh the init task doc for this project and route Claude through the installed Superpowers plugin.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title] [optional goal]
---

Run the project-local so2x-system init flow.

Steps:
1. Confirm `.so2x-system/scripts/execute.py` exists.
2. Confirm Superpowers is installed in Claude. If it is not installed, stop and tell the user to run `/plugin install superpowers@claude-plugins-official` or `/plugin install superpowers@superpowers-marketplace` first.
3. If the user supplied arguments, treat the first phrase as the title and the rest as goal/scope.
4. Run `python3 .so2x-system/scripts/execute.py flow-init --title "<title>" --goal "<goal>"`.
5. Read `run_output`, check `gate_results`, then follow `dispatch_plan` in order and execute each `superpowers:*` skill target.
6. Summarize the created task doc path and the next action briefly.

If no title was provided, default to `Initialize project workflow`.
