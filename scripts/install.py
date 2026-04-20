#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
COPY_DIRS = ['.claude', 'config', 'commands', 'docs', 'scripts', 'src', 'tasks', 'signals', 'candidates', 'outputs', 'state']
SKIP_NAMES = {'__pycache__', '.git', '.pytest_cache', 'tests', 'README.md'}
TASK_TEMPLATE_SUFFIXES = {'.gitkeep'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Install so2x-system into a target project')
    parser.add_argument('--target', default='.', help='Target project root (default: current directory)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing files')
    parser.add_argument('--patch-claude-md', action='store_true', help='Reserved for future Claude guidance patching')
    return parser.parse_args()


def should_skip(rel: Path) -> bool:
    if any(part in SKIP_NAMES for part in rel.parts):
        return True
    if rel.parts and rel.parts[0] in {'tasks', 'signals', 'candidates', 'outputs'}:
        return rel.name not in TASK_TEMPLATE_SUFFIXES
    return False


def target_rel(rel: Path) -> Path:
    if rel.parts[0] == '.claude':
        return rel
    return Path('.so2x-system') / rel


def copy_file(src: Path, dst: Path, force: bool) -> bool:
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def install_tree(target_root: Path, force: bool) -> list[str]:
    copied: list[str] = []
    for rel_dir in COPY_DIRS:
        src_root = SOURCE_ROOT / rel_dir
        for src in sorted(src_root.rglob('*')):
            if src.is_dir():
                continue
            rel = src.relative_to(SOURCE_ROOT)
            if should_skip(rel):
                continue
            dst = target_root / target_rel(rel)
            if copy_file(src, dst, force):
                copied.append(str(target_rel(rel)))
    return copied


def verify_install(target_root: Path) -> list[str]:
    required = [
        '.so2x-system/scripts/execute.py',
        '.so2x-system/config/routing.yaml',
        '.so2x-system/docs/PRD.md',
        '.claude/commands/flow-init.md',
    ]
    return [rel for rel in required if not (target_root / rel).exists()]


def main() -> int:
    args = parse_args()
    target_root = Path(args.target).resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    print('step 1/4: copy scaffold files')
    copied = install_tree(target_root, force=args.force)

    print('step 2/4: verify required files')
    missing = verify_install(target_root)
    if missing:
        for rel in missing:
            print(f'missing: {rel}')
        raise SystemExit(1)

    print('step 3/4: patch CLAUDE.md')
    print(f'claude_md_patched: {False}')

    print('step 4/4: install complete')
    print('next_step: flow-init으로 이 프로젝트를 초기화해줘.')
    print('next_step_cli: /flow-init')
    print('next_step_human: 다음 단계: /flow-init으로 프로젝트를 초기화하세요.')
    print(f'target: {target_root}')
    print(f'copied_count: {len(copied)}')
    for item in copied:
        print(item)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
