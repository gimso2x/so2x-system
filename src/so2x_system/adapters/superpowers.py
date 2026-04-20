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


def normalize_skill_result(raw_payload: dict[str, Any], base_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw_payload)
    payload.setdefault("status", "success")
    payload.setdefault("artifacts", [])
    payload.setdefault("summary", "")
    payload.setdefault("next_steps", [])
    payload.update({k: v for k, v in base_payload.items() if k not in payload})
    return payload


def allow_simulated_superpowers() -> bool:
    return os.environ.get("SO2X_SYSTEM_ALLOW_SIMULATED_SUPERPOWERS", "").strip().lower() in {"1", "true", "yes", "on"}


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
        "input": {
            "task_doc": str(task_doc),
            "mode": mode,
            "verification": verification or "not-provided",
        },
    }
    if not command:
        if allow_simulated_superpowers():
            return normalize_skill_result(
                {
                    "status": "simulated",
                    "summary": "superpowers execution simulated because no external runner was configured",
                    "next_steps": [
                        "Configure SO2X_SYSTEM_SUPERPOWER_COMMAND to execute real superpowers steps.",
                    ],
                },
                base_payload,
            )
        return normalize_skill_result(
            {
                "status": "failed",
                "stderr": (
                    "SO2X_SYSTEM_SUPERPOWER_COMMAND is not configured. "
                    "Install and enable the superpowers plugin for Claude, or set "
                    "SO2X_SYSTEM_SUPERPOWER_COMMAND for shell/CI execution."
                ),
                "summary": "superpowers execution runner missing",
                "next_steps": [
                    "Install and enable superpowers in Claude.",
                    "Or set SO2X_SYSTEM_SUPERPOWER_COMMAND to a real external runner.",
                ],
            },
            base_payload,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        prompt_file = tmpdir_path / "prompt.txt"
        rules_file = tmpdir_path / "rules.json"
        output_file = tmpdir_path / "result.json"
        prompt_file.write_text(prompt_text, encoding="utf-8")
        rules_file.write_text(json.dumps(approved_rules, indent=2) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                *command,
                "--step",
                skill_name,
                "--prompt-file",
                str(prompt_file),
                "--task-doc",
                str(task_doc),
                "--rules-file",
                str(rules_file),
                "--output-file",
                str(output_file),
            ],
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
                "artifacts": [],
                "summary": "",
                "next_steps": [],
            }

        if output_file.exists():
            raw_text = output_file.read_text(encoding="utf-8").strip()
            payload = json.loads(raw_text) if raw_text else {"status": "success"}
            return normalize_skill_result(payload, base_payload)

        stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not stdout_lines:
            return normalize_skill_result({"status": "success"}, base_payload)
        try:
            payload = json.loads(stdout_lines[-1])
        except json.JSONDecodeError:
            return {
                **base_payload,
                "status": "failed",
                "stderr": "invalid json contract",
                "stdout": proc.stdout,
                "artifacts": [],
                "summary": "",
                "next_steps": [],
            }
        return normalize_skill_result(payload, base_payload)
