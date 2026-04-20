from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def render_superpowers_prompt(
    *,
    step_id: str,
    skill_name: str,
    mode: str,
    title: str,
    goal: str,
    verification: str,
    task_doc: Path,
    approved_rules: list[dict[str, Any]],
) -> str:
    rules_text = "\n".join(f"- {rule['pattern']} ({rule['recommendation']})" for rule in approved_rules) or "- none"
    return (
        f"step_id: {step_id}\n"
        f"skill: {skill_name}\n"
        f"mode: {mode}\n"
        f"title: {title}\n"
        f"goal: {goal or 'n/a'}\n"
        f"task_doc: {task_doc}\n"
        f"verification: {verification or 'n/a'}\n"
        f"approved_rules:\n{rules_text}\n"
    )


def run_superpowers_skill(
    step: dict[str, Any],
    *,
    mode: str,
    title: str,
    goal: str,
    verification: str,
    task_doc: Path,
    approved_rules: list[dict[str, Any]],
    cwd: Path,
) -> dict[str, Any]:
    step_id = step["id"]
    skill_name = step["target"]
    prompt_text = render_superpowers_prompt(
        step_id=step_id,
        skill_name=skill_name,
        mode=mode,
        title=title,
        goal=goal,
        verification=verification,
        task_doc=task_doc,
        approved_rules=approved_rules,
    )

    command = shlex.split(os.environ.get("SO2X_SYSTEM_SUPERPOWER_COMMAND", "").strip())
    base_payload = {
        "step_id": step_id,
        "kind": "skill",
        "target": skill_name,
        "prompt": prompt_text,
    }
    if not command:
        return {**base_payload, "status": "simulated"}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        prompt_file = tmpdir_path / "prompt.txt"
        rules_file = tmpdir_path / "rules.json"
        prompt_file.write_text(prompt_text, encoding="utf-8")
        rules_file.write_text(json.dumps(approved_rules, indent=2) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [*command, "--step", skill_name, "--prompt-file", str(prompt_file), "--task-doc", str(task_doc), "--rules-file", str(rules_file)],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )

    if proc.returncode != 0:
        return {
            **base_payload,
            "status": "failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    payload = json.loads(proc.stdout) if proc.stdout.strip() else {"status": "success"}
    payload.update({k: v for k, v in base_payload.items() if k not in payload})
    payload.setdefault("status", "success")
    return payload
