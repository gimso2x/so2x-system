import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXECUTE = ROOT / "scripts" / "execute.py"


def run_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXECUTE), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_flow_feature_creates_task_run_signal_and_state() -> None:
    workspace = Path("/tmp/so2x-system-feature-test")
    if workspace.exists():
        subprocess.run(["rm", "-rf", str(workspace)], check=True)
    subprocess.run(["cp", "-R", str(ROOT), str(workspace)], check=True)

    result = subprocess.run(
        [sys.executable, str(workspace / "scripts" / "execute.py"), "flow-feature", "--title", "Add signal promotion", "--goal", "Promote repeated patterns into candidate rules", "--files", "src/so2x_system/runner.py,docs/RULES.md", "--verification", "pytest", "--notes", "Start from the plan"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = __import__("json").loads(result.stdout)
    assert (workspace / payload["task_doc"]).exists()
    assert (workspace / payload["run_output"]).exists()
    assert (workspace / payload["signal_output"]).exists()


def test_self_improve_promotes_repeated_patterns() -> None:
    workspace = Path("/tmp/so2x-system-self-improve-test")
    if workspace.exists():
        subprocess.run(["rm", "-rf", str(workspace)], check=True)
    subprocess.run(["cp", "-R", str(ROOT), str(workspace)], check=True)

    for _ in range(3):
        result = subprocess.run(
            [sys.executable, str(workspace / "scripts" / "execute.py"), "flow-qa", "--title", "Missing browser proof", "--goal", "Capture recurring QA misses", "--pattern", "browser verification missing"],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    result = subprocess.run(
        [sys.executable, str(workspace / "scripts" / "execute.py"), "self-improve", "--title", "Promote repeated QA failures"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = __import__("json").loads(result.stdout)
    assert payload["candidate_outputs"]
    candidate_text = (workspace / payload["candidate_outputs"][0]).read_text()
    assert "browser verification missing" in candidate_text
    assert "candidate hard gate" in candidate_text.lower()
