---
description: Create a QA task doc and route debugging work through installed Superpowers skills.
allowed-tools: Bash(python3 .so2x-system/scripts/execute.py:*),Read,Write
argument-hint: [title] [goal]
---

1. Confirm Superpowers is installed in Claude. If not, stop and tell the user to install the plugin first.
2. Run `python3 .so2x-system/scripts/execute.py flow-qa --title "<title>" --goal "<goal>"` using the user request.
3. Follow the routed Superpowers flow from the generated run output, especially `systematic-debugging`.
4. Respect any approved rules or gate blockers recorded by so2x-system before continuing.

Default title: `QA task`.
