from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
COPY_EXCLUDE = shutil.ignore_patterns(
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "*.pyc",
)


def make_workspace(name: str) -> Path:
    workspace = Path("/tmp") / f"so2x-system-{name}"
    shutil.rmtree(workspace, ignore_errors=True)
    shutil.copytree(SOURCE_ROOT, workspace, ignore=COPY_EXCLUDE)
    return workspace


def run_cmd(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = workspace / "scripts" / "execute.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )


def test_flow_feature_creates_task_run_signal_and_state() -> None:
    root = make_workspace("feature")

    result = run_cmd(
        root,
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
    task_path = root / payload["task_doc"]
    run_path = root / payload["run_output"]
    signal_path = root / payload["signal_output"]
    history_path = root / "state" / "history.jsonl"
    metrics_path = root / "state" / "metrics.json"

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
    root = make_workspace("self-improve")

    for _ in range(3):
        result = run_cmd(
            root,
            "flow-qa",
            "--title",
            "Missing browser proof",
            "--goal",
            "Capture recurring QA misses",
            "--pattern",
            "browser verification missing",
        )
        assert result.returncode == 0, result.stderr

    result = run_cmd(root, "self-improve", "--title", "Promote repeated QA failures")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["candidate_outputs"]
    candidate_path = root / payload["candidate_outputs"][0]
    assert candidate_path.exists()

    candidate_text = candidate_path.read_text()
    assert "browser verification missing" in candidate_text
    assert "candidate hard gate" in candidate_text.lower()
