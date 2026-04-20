import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.py"


def run_install(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALL), "--target", str(target), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def test_install_copies_claude_command_surface_and_system_scaffold(tmp_path: Path) -> None:
    target = tmp_path / "app"
    result = run_install(target)

    assert "step 1/4: copy scaffold files" in result.stdout
    assert "step 4/4: install complete" in result.stdout
    assert "next_step_cli: /flow-init" in result.stdout
    assert (target / ".so2x-system" / "scripts" / "execute.py").exists()
    assert (target / ".so2x-system" / "config" / "routing.yaml").exists()
    assert (target / ".so2x-system" / "docs" / "PRD.md").exists()
    assert (target / ".claude" / "commands" / "flow-init.md").exists()
    assert (target / ".claude" / "commands" / "flow-feature.md").exists()


def test_install_does_not_overwrite_existing_files_without_force(tmp_path: Path) -> None:
    target = tmp_path / "app"
    existing = target / ".so2x-system" / "docs" / "PRD.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("keep me\n", encoding="utf-8")

    run_install(target)

    assert existing.read_text(encoding="utf-8") == "keep me\n"


def test_install_force_overwrites_existing_files(tmp_path: Path) -> None:
    target = tmp_path / "app"
    existing = target / ".so2x-system" / "docs" / "PRD.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old\n", encoding="utf-8")

    run_install(target, "--force")

    assert "so2x-system" in existing.read_text(encoding="utf-8")


def test_claude_command_calls_project_local_runner_and_requires_superpowers() -> None:
    command_doc = (ROOT / ".claude" / "commands" / "flow-init.md").read_text(encoding="utf-8")

    assert "python3 .so2x-system/scripts/execute.py flow-init" in command_doc
    assert "allowed-tools:" in command_doc
    assert "/plugin install superpowers@claude-plugins-official" in command_doc


def test_readme_documents_project_local_ai_install_flow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "현재 프로젝트 루트를 기준으로 so2x-system을 설치해줘." in readme
    assert "전역 설치가 아니라 현재 프로젝트 내부 설치" in readme
    assert "python3 .tmp/so2x-system/scripts/install.py --target . --patch-claude-md" in readme
    assert "test -f .claude/commands/flow-init.md" in readme
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme


def test_readme_documents_shell_install_flow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "mkdir -p .tmp" in readme
    assert "python3 .tmp/so2x-system/scripts/install.py --target ." in readme
    assert "rm -rf .tmp/so2x-system" in readme
    assert "rmdir .tmp 2>/dev/null || true" in readme
    assert "test -f .so2x-system/scripts/execute.py" in readme
    assert "test -f .claude/commands/flow-init.md" in readme


def test_readme_documents_superpowers_plugin_prerequisite() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "superpowers plugin은 별도로 설치" in readme
    assert "/plugin install superpowers@claude-plugins-official" in readme
    assert "https://github.com/obra/superpowers" in readme
