---
description: Create or refresh the init task doc for this project.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title] [optional goal]
---

Run the project-local so2x-system init flow.

Steps:
1. Confirm `.so2x-system/scripts/execute.py` exists.
2. If the user supplied arguments, treat the first phrase as the title and the rest as goal/scope.
3. Run `python3 .so2x-system/scripts/execute.py flow-init --title "<title>" --goal "<goal>"`.
4. Summarize the created task doc path and the next action briefly.

If no title was provided, default to `Initialize project workflow`.
