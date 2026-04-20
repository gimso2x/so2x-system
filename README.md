# so2x-system

so2x-system은 `superpowers`를 대체하지 않는다.
**superpowers를 감싸는 wrapper**로서, 프로젝트 로컬에 설치되어 Claude slash command와 run 기록/학습 루프를 붙인다.
전역 설치가 아니라 현재 프로젝트 내부 설치를 기본으로 본다.

핵심 역할은 4가지다.
- task 문서를 먼저 만든다
- `dispatch_plan` / `gate_results` / `dispatch_results` 계약을 만든다
- signal / state / candidate를 기록한다
- 승인된 규칙을 다음 실행에 재주입한다

## 역할 분담

- `superpowers`: 실제 실행 skill
- `so2x-system`: routing, gate, 기록, 승격, 재주입

즉 흐름은 이렇다.

```text
사용자 요청
-> .claude/commands/*.md
-> .so2x-system/scripts/execute.py
-> runner가 task/run/signal/state 생성
-> dispatch_plan 생성
-> gate_results 생성
-> Claude가 gate_results를 먼저 확인
-> dispatch_plan 순서대로 superpowers:* skill 실행
-> dispatch_results 기록
-> 반복되면 rule/gate 후보로 승격
```

## superpowers plugin 선설치

so2x-system은 **superpowers plugin을 번들하지 않는다.**
즉 superpowers plugin은 별도로 설치해야 한다.
먼저 Claude에 superpowers를 따로 설치해야 한다.

공식 설치 예:
```text
/plugin install superpowers@claude-plugins-official
```

또는 marketplace:
```text
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

참고:
- `https://github.com/obra/superpowers`

## 빠른 설치

준비물:
- Claude Code
- Git
- Python 3.11+
- 설치된 superpowers plugin

### 방법 A — AI에게 설치시키기

프로젝트 루트에서 아래 프롬프트를 그대로 주면 된다.

```text
현재 프로젝트 루트를 기준으로 so2x-system을 설치해줘. 중간 확인 질문 없이 한국어로 진행하고, 새 설계 문서나 task 문서는 만들지 마.
그리고 superpowers plugin이 아직 없으면 먼저 Claude에서 `/plugin install superpowers@claude-plugins-official` 로 설치하라고 짧게 알려줘.
중간 단계 성공만 보고하고 응답을 끝내지 말고, 아래 1~5단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해.
recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고, 실제 실행이 남아 있으면 계속 진행해.

1. `mkdir -p .tmp` 를 실행해.
2. `git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-system.git .tmp/so2x-system` 를 실행해.
3. `python3 .tmp/so2x-system/scripts/install.py --target . --patch-claude-md` 를 실행해.
4. `test -f .so2x-system/scripts/execute.py && test -f .so2x-system/config/routing.yaml && test -f .claude/commands/flow-init.md` 로 설치 결과를 확인해.
5. `rm -rf .tmp/so2x-system && rmdir .tmp 2>/dev/null || true` 를 실행해 정리하고, 마지막 한 줄에는 반드시 다음 실행 안내를 넣어. 문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써.
```

### 방법 B — 셸에서 직접 설치

```bash
mkdir -p .tmp
git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-system.git .tmp/so2x-system
python3 .tmp/so2x-system/scripts/install.py --target .
test -f .so2x-system/scripts/execute.py
test -f .so2x-system/config/routing.yaml
test -f .claude/commands/flow-init.md
rm -rf .tmp/so2x-system
rmdir .tmp 2>/dev/null || true
```

## 설치 결과

설치 후 프로젝트에는 두 축이 생긴다.

```text
your-project/
├── .claude/
│   └── commands/
│       ├── flow-init.md
│       ├── flow-feature.md
│       ├── flow-qa.md
│       ├── flow-review.md
│       └── self-improve.md
└── .so2x-system/
    ├── config/
    ├── docs/
    ├── scripts/
    ├── src/
    ├── tasks/
    ├── signals/
    ├── candidates/
    ├── outputs/
    └── state/
```

- `.claude/commands/` = Claude slash command surface
- `.so2x-system/` = 로컬 runtime/state scaffold
- 실제 skill execution = 설치된 superpowers plugin
- superpowers는 Claude 안에서 **installed and enabled** 상태여야 실제 dispatch가 실행된다
- 실행기가 없으면 run output은 `simulated` 또는 명시적 `failed` 상태로 남는다

## 현재 routing 개요

현재 기본 흐름은 이렇다.

- feature
  - `superpowers:brainstorming`
  - `superpowers:writing-plans`
  - `superpowers:subagent-driven-development`
- qa
  - `superpowers:systematic-debugging`
  - `superpowers:verification-before-completion`
- review
  - `superpowers:requesting-code-review`
- self-improve
  - local internal step만 수행

## 실행 계약

run output의 핵심 surface는 3개다.

- `dispatch_plan`
  - 실행 전 계약
  - 각 step은 `step_id`, `kind`, `target`, `input`을 가진다
- `gate_results`
  - gate 판정 결과
  - `passed` 또는 `blocked`
- `dispatch_results`
  - 실제 step 실행 기록
  - plan과 같은 `step_id` / `input` 축을 유지한다

예를 들면:

```json
{
  "dispatch_plan": [
    {
      "step_id": "feature-plan",
      "kind": "skill",
      "target": "superpowers:writing-plans",
      "input": {
        "task_doc": "tasks/feature/task-001-example.md",
        "mode": "flow-feature",
        "verification": "not-provided"
      }
    }
  ],
  "gate_results": {
    "status": "passed",
    "blockers": []
  },
  "dispatch_results": [
    {
      "step_id": "feature-plan",
      "kind": "skill",
      "target": "superpowers:writing-plans",
      "input": {
        "task_doc": "tasks/feature/task-001-example.md",
        "mode": "flow-feature",
        "verification": "not-provided"
      },
      "status": "success",
      "summary": "executed superpowers:writing-plans",
      "artifacts": [],
      "next_steps": []
    }
  ]
}
```

## gate / signal

현재 browser verification gate는 설정 기반 힌트로 판정한다.

- UI file hints
  - `.tsx`, `.jsx`, `app/`, `components/`, `pages/`, `public/`
- verification hints
  - `browser`, `playwright`, `snapshot`, `qa`

즉 단순히 문장에 `ui`가 있는지 보는 게 아니라,
**파일 힌트 + verification 힌트**로 gate와 signal을 같이 판정한다.

## 실행 예시

Claude에서는:
```text
/flow-init
/flow-feature 결제 기능 첫 slice 구현
/flow-qa 로그인 실패 재현부터 잡기
/self-improve 반복된 QA 실패 승격
```

직접 실행도 가능하다:
```bash
python3 .so2x-system/scripts/execute.py flow-init --title "Initialize project workflow"
python3 .so2x-system/scripts/execute.py flow-feature --title "Add rule promotion" --goal "Turn repeated patterns into candidates"
python3 .so2x-system/scripts/execute.py flow-qa --title "Fix failing browser proof" --goal "Capture QA misses" --pattern "browser verification missing"
python3 .so2x-system/scripts/execute.py self-improve --title "Promote recurring failures"
```

외부 실행기를 붙이고 싶으면:
```bash
export SO2X_SYSTEM_SUPERPOWER_COMMAND="python3 ./mock_superpower_runner.py"
python3 .so2x-system/scripts/execute.py flow-feature --title "Example" --goal "Dispatch plan steps"
```

adapter 계약:
- 우선 `--output-file <tmp.json>` 결과 파일을 읽는다
- 파일이 없으면 stdout 마지막 JSON line을 fallback으로 읽는다
- fallback JSON이 깨져 있으면 `status: failed`, `stderr: invalid json contract`로 기록한다

## 테스트

```bash
pytest -q
```

또는 최소 회귀 검증:

```bash
python3 -m pytest tests/test_install.py tests/test_execute.py -q
```

## 제한사항

중요:
- Python이 Claude plugin skill을 직접 호출하는 건 아니다
- 실제 superpowers skill execution은 여전히 Claude command layer / external runner를 통해 이뤄진다
- so2x-system은 그 앞뒤에서 계약, gate, 기록, 학습을 담당한다

## 다음 단계

다음 단계: /flow-init으로 프로젝트를 초기화하세요.
