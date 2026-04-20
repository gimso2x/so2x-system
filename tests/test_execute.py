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
parser.add_argument('--output-file', required=True)
args = parser.parse_args()

payload = {
    'summary': f"executed {args.step}",
    'artifacts': [args.task_doc],
    'next_steps': [],
    'runner_step': args.step,
    'prompt': Path(args.prompt_file).read_text(encoding='utf-8'),
    'task_doc': Path(args.task_doc).read_text(encoding='utf-8'),
    'rules': json.loads(Path(args.rules_file).read_text(encoding='utf-8')),
    'status': 'success',
}
Path(args.output_file).write_text(json.dumps(payload), encoding='utf-8')
print('mock-runner completed')
'''


MOCK_STDOUT_ONLY_RUNNER = '''from __future__ import annotations

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('--step', required=True)
parser.add_argument('--prompt-file', required=True)
parser.add_argument('--task-doc', required=True)
parser.add_argument('--rules-file', required=True)
parser.add_argument('--output-file', required=True)
args = parser.parse_args()

print('log before result')
print(json.dumps({'status': 'success', 'summary': f'stdout {args.step}', 'artifacts': [], 'next_steps': ['done']}))
'''


MOCK_INVALID_STDOUT_RUNNER = '''from __future__ import annotations

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--step', required=True)
parser.add_argument('--prompt-file', required=True)
parser.add_argument('--task-doc', required=True)
parser.add_argument('--rules-file', required=True)
parser.add_argument('--output-file', required=True)
parser.parse_args()

print('not-json-last-line')
'''


def make_workspace(name: str) -> Path:
    workspace = Path('/tmp') / f'so2x-system-{name}'
    shutil.rmtree(workspace, ignore_errors=True)
    shutil.copytree(SOURCE_ROOT, workspace, ignore=COPY_EXCLUDE)
    return workspace


def write_mock_runner(workspace: Path, content: str = MOCK_RUNNER, filename: str = 'mock_superpower_runner.py') -> Path:
    path = workspace / filename
    path.write_text(content, encoding='utf-8')
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
    assert [step['step_id'] for step in run_output['dispatch_plan']] == [
        'feature-brainstorm',
        'feature-plan',
        'feature-build',
    ]
    assert [step['target'] for step in run_output['dispatch_plan']] == [
        'superpowers:brainstorming',
        'superpowers:writing-plans',
        'superpowers:subagent-driven-development',
    ]
    assert run_output['dispatch_plan'][0]['input']['mode'] == 'flow-feature'
    assert run_output['gate_results'] == {'status': 'passed', 'blockers': []}
    assert [step['step_id'] for step in run_output['dispatch_results']] == [
        'feature-brainstorm',
        'feature-plan',
        'feature-build',
    ]
    assert [step['input'] for step in run_output['dispatch_results']] == [step['input'] for step in run_output['dispatch_plan']]
    assert all(step['status'] == 'success' for step in run_output['dispatch_results'])
    assert run_output['dispatch_results'][0]['summary'] == 'executed superpowers:brainstorming'


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
        qa_payload = json.loads(qa_result.stdout)
        qa_run = json.loads((root / qa_payload['run_output']).read_text(encoding='utf-8'))
        assert [step['step_id'] for step in qa_run['dispatch_plan']] == ['qa-debug', 'qa-verify']
        assert [step['input'] for step in qa_run['dispatch_results']] == [step['input'] for step in qa_run['dispatch_plan']]

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
        'Checkout polish',
        '--goal',
        'Exercise approved gate',
        '--files',
        'app/checkout/page.tsx,components/CheckoutButton.tsx',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )
    assert gated_result.returncode == 2
    gated_payload = json.loads(gated_result.stdout)
    blocked_run = json.loads((root / gated_payload['run_output']).read_text(encoding='utf-8'))
    assert blocked_run['status'] == 'blocked'
    assert blocked_run['gate_results'] == {'status': 'blocked', 'blockers': ['browser_verification']}

    allowed_result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'Checkout polish verified',
        '--goal',
        'Exercise approved rule injection',
        '--files',
        'app/checkout/page.tsx',
        '--verification',
        'playwright browser snapshot attached',
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

    assert [step['step_id'] for step in run_output['dispatch_plan']] == [
        'improve-pattern-analysis',
        'improve-writing-skills',
    ]
    assert run_output['gate_results'] == {'status': 'passed', 'blockers': []}
    assert [step['kind'] for step in run_output['dispatch_results']] == ['internal', 'internal']
    assert [step['input'] for step in run_output['dispatch_results']] == [step['input'] for step in run_output['dispatch_plan']]
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
        'Add checkout slice',
        '--goal',
        'Change the checkout screen',
        '--files',
        'app/checkout/page.tsx,components/CheckoutButton.tsx',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    signal_output = json.loads((root / payload['signal_output']).read_text(encoding='utf-8'))

    assert signal_output['type'] == 'feature_run'
    assert signal_output['pattern'] == 'browser verification missing'
    assert signal_output['notes'] == 'UI-oriented work ran without browser proof in verification context'


def test_adapter_falls_back_to_last_stdout_json_line_when_output_file_missing() -> None:
    root = make_workspace('stdout-fallback')
    runner = write_mock_runner(root, content=MOCK_STDOUT_ONLY_RUNNER, filename='stdout_runner.py')

    result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'CLI-only change',
        '--goal',
        'Exercise stdout fallback',
        '--files',
        'src/cli.py',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    run_output = json.loads((root / payload['run_output']).read_text(encoding='utf-8'))
    first_step = run_output['dispatch_results'][0]

    assert first_step['summary'] == 'stdout superpowers:brainstorming'
    assert first_step['next_steps'] == ['done']


def test_adapter_marks_invalid_stdout_json_contract_as_failed() -> None:
    root = make_workspace('stdout-invalid')
    runner = write_mock_runner(root, content=MOCK_INVALID_STDOUT_RUNNER, filename='invalid_stdout_runner.py')

    result = run_cmd(
        root,
        'flow-feature',
        '--title',
        'CLI-only change',
        '--goal',
        'Exercise invalid stdout contract',
        '--files',
        'src/cli.py',
        env={'SO2X_SYSTEM_SUPERPOWER_COMMAND': f'{sys.executable} {runner}'},
    )

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    run_output = json.loads((root / payload['run_output']).read_text(encoding='utf-8'))
    first_step = run_output['dispatch_results'][0]

    assert first_step['status'] == 'failed'
    assert first_step['stderr'] == 'invalid json contract'
    assert first_step['input'] == run_output['dispatch_plan'][0]['input']
