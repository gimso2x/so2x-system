from __future__ import annotations

import json
import os
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


MOCK_RUNNER = '''from __future__ import annotations

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--step', required=True)
parser.add_argument('--prompt-file', required=True)
parser.add_argument('--task-doc', required=True)
parser.add_argument('--rules-file', required=True)
args = parser.parse_args()

payload = {
    'step': args.step,
    'prompt': Path(args.prompt_file).read_text(encoding='utf-8'),
    'task_doc': Path(args.task_doc).read_text(encoding='utf-8'),
    'rules': json.loads(Path(args.rules_file).read_text(encoding='utf-8')),
    'status': 'success',
}
print(json.dumps(payload))
'''


def make_workspace(name: str) -> Path:
    workspace = Path('/tmp') / f'so2x-system-{name}'
    shutil.rmtree(workspace, ignore_errors=True)
    shutil.copytree(SOURCE_ROOT, workspace, ignore=COPY_EXCLUDE)
    return workspace


def write_mock_runner(workspace: Path) -> Path:
    path = workspace / 'mock_superpower_runner.py'
    path.write_text(MOCK_RUNNER, encoding='utf-8')
    return path


def run_cmd(workspace: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    script = workspace / 'scripts' / 'execute.py'
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
    )


def test_flow_feature_dispatches_superpower_steps_and_records_results() -> None:
    root = make_workspace('dispatch')
    runner = write_mock_runner(root)

    result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'Add signal promotion',
        '--goal',
        'Promote repeated patterns into candidate rules',
        '--files',
        'src/so2x_system/runner.py,docs/RULES.md',
        '--verification',
        'pytest browser',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    run_output = json.loads((root / payload['run_output']).read_text(encoding='utf-8'))

    assert run_output['status'] == 'success'
    assert [step['step_id'] for step in run_output['dispatch_results']] == [
        'feature-brainstorm',
        'feature-plan',
        'feature-build',
    ]
    assert [step['kind'] for step in run_output['dispatch_results']] == ['skill', 'skill', 'skill']
    assert [step['target'] for step in run_output['dispatch_results']] == [
        'superpowers:brainstorming',
        'superpowers:writing-plans',
        'superpowers:subagent-driven-development',
    ]
    assert all(step['status'] == 'success' for step in run_output['dispatch_results'])


def test_approved_rule_is_reapplied_to_future_runs() -> None:
    root = make_workspace('approved-rules')
    runner = write_mock_runner(root)

    for _ in range(3):
        qa_result = run_cmd(
            root,
            'flow-qa',
            '--title',
            'Missing browser proof',
            '--goal',
            'Capture recurring QA misses',
            '--pattern',
            'browser verification missing',
            '--verification',
            'browser check',
            env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
        )
        assert qa_result.returncode == 0, qa_result.stderr

    improve_result = run_cmd(root, 'self-improve', '--title', 'Promote repeated QA failures')
    assert improve_result.returncode == 0, improve_result.stderr
    improve_payload = json.loads(improve_result.stdout)
    candidate_path = root / improve_payload['candidate_outputs'][0]

    candidate_text = candidate_path.read_text(encoding='utf-8').replace('approved: false', 'approved: true')
    candidate_path.write_text(candidate_text, encoding='utf-8')

    gated_result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'UI change without browser proof',
        '--goal',
        'Exercise approved gate',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )
    assert gated_result.returncode == 2
    gated_payload = json.loads(gated_result.stdout)
    blocked_run = json.loads((root / gated_payload['run_output']).read_text(encoding='utf-8'))
    assert blocked_run['status'] == 'blocked'
    assert blocked_run['blocked_by'] == ['browser_verification']

    allowed_result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'UI change with browser proof',
        '--goal',
        'Exercise approved rule injection',
        '--verification',
        'browser proof attached',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )
    assert allowed_result.returncode == 0, allowed_result.stderr
    allowed_payload = json.loads(allowed_result.stdout)
    allowed_run = json.loads((root / allowed_payload['run_output']).read_text(encoding='utf-8'))

    assert allowed_run['approved_rules']
    assert allowed_run['approved_rules'][0]['pattern'] == 'browser verification missing'
    assert 'browser verification missing' in allowed_run['dispatch_results'][0]['prompt']


def test_self_improve_dispatches_internal_steps_only() -> None:
    root = make_workspace('self-improve')
    runner = write_mock_runner(root)

    result = run_cmd(
        root,
        'self-improve',
        '--title',
        'Promote repeated QA failures',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    run_output = json.loads((root / payload['run_output']).read_text(encoding='utf-8'))

    assert [step['kind'] for step in run_output['dispatch_results']] == ['internal', 'internal']
    assert [step['target'] for step in run_output['dispatch_results']] == [
        'pattern-analysis',
        'writing-skills',
    ]


def test_signal_classifies_missing_browser_verification_pattern() -> None:
    root = make_workspace('signal-classifier')
    runner = write_mock_runner(root)

    result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'Add UI slice',
        '--goal',
        'Change the checkout UI',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    signal_output = json.loads((root / payload['signal_output']).read_text(encoding='utf-8'))

    assert signal_output['type'] == 'feature_run'
    assert signal_output['pattern'] == 'browser verification missing'
    assert signal_output['notes'] == 'UI-oriented work ran without browser proof in verification context'
