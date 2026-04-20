from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_project_local_ai_install_flow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "현재 프로젝트 루트를 기준으로 so2x-system을 설치해줘." in readme
    assert "전역 설치가 아니라 현재 프로젝트 내부 설치" in readme
    assert "git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-system.git .tmp/so2x-system" in readme
    assert "cp -R .tmp/so2x-system/config .so2x-system/" in readme
    assert "cp -R .tmp/so2x-system/commands .so2x-system/" in readme
    assert "cp -R .tmp/so2x-system/docs .so2x-system/" in readme
    assert "cp -R .tmp/so2x-system/scripts .so2x-system/" in readme
    assert "다음 단계: /flow-init으로 프로젝트를 초기화하세요." in readme


def test_readme_documents_shell_install_flow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "mkdir -p .tmp .so2x-system" in readme
    assert "rm -rf .tmp/so2x-system" in readme
    assert "rmdir .tmp 2>/dev/null || true" in readme
    assert "test -f .so2x-system/scripts/execute.py" in readme
    assert "test -f .so2x-system/config/routing.yaml" in readme
