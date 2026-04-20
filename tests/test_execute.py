from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "execute.py"
RESET_PATHS = [
    ROOT / "tasks" / "feature",
    ROOT / "tasks" / "qa",
    ROOT / "tasks" / "review",
    ROOT / "signals" / "fixes",
    ROOT / "signals" / "qa-failures",
    ROOT / "signals" / "review-notes",
    ROOT / "signals" / "repeated-patterns",
    ROOT / "candidates" / "rules",
    ROOT / "candidates" / "skills",
    ROOT / "outputs" / "runs",
    ROOT / "state",
]


def reset_repo_state() -> None:
    for path in RESET_PATHS:
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        if path.parts[-2:] in [
            ("tasks", "feature"),
            ("tasks", "qa"),
            ("tasks", "review"),
            ("signals", "fixes"),
            ("signals", "qa-failures"),
            ("signals", "review-notes"),
            ("signals", "repeated-patterns"),
            ("candidates", "rules"),
            ("candidates", "skills"),
            ("outputs", "runs"),
        ]:
            (path / ".gitkeep").write_text("")


def run_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_flow_feature_creates_task_run_signal_and_state() -> None:
    reset_repo_state()

    result = run_cmd(
        "flow-feature",
        "--title",
        "Add signal promotion",
        "--goal",
        "Promote repeated patterns into candidate rules",
        "--files",
        "src/so2x_system/runner.py,docs/RULES.md",
        "--verification",
        "pytest",
        "--notes",
        "Start from the plan",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    task_path = ROOT / payload["task_doc"]
    run_path = ROOT / payload["run_output"]
    signal_path = ROOT / payload["signal_output"]
    history_path = ROOT / "state" / "history.jsonl"
    metrics_path = ROOT / "state" / "metrics.json"

    assert task_path.exists()
    assert run_path.exists()
    assert signal_path.exists()
    assert history_path.exists()
    assert metrics_path.exists()
    assert "Add signal promotion" in task_path.read_text()

    metrics = json.loads(metrics_path.read_text())
    assert metrics["runs_by_mode"]["feature"] == 1
    assert metrics["signals_by_type"]["feature_run"] == 1


def test_self_improve_promotes_repeated_patterns() -> None:
    reset_repo_state()

    for _ in range(3):
        result = run_cmd(
            "flow-qa",
            "--title",
            "Missing browser proof",
            "--goal",
            "Capture recurring QA misses",
            "--pattern",
            "browser verification missing",
        )
        assert result.returncode == 0, result.stderr

    result = run_cmd("self-improve", "--title", "Promote repeated QA failures")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["candidate_outputs"]
    candidate_path = ROOT / payload["candidate_outputs"][0]
    assert candidate_path.exists()

    candidate_text = candidate_path.read_text()
    assert "browser verification missing" in candidate_text
    assert "candidate hard gate" in candidate_text.lower()
