# so2x-system

so2x-system은 superpowers 실행 스타일을 빌리되, **각 프로젝트에 로컬 설치해서 Claude에서도 바로 `/flow-init` 같은 slash command로 쓰는 얇은 시스템 스캐폴드**다.
전역 설치가 아니라 현재 프로젝트 내부 설치를 기본으로 본다.

핵심은 간단하다.
- task 문서를 먼저 만든다
- feature/qa/review/self-improve 흐름을 라우팅한다
- run output / signal / state를 남긴다
- 반복 패턴을 rule/skill/gate 후보로 승격한다
- Claude command surface와 연결해서 `/flow-init` 같은 진입점을 바로 쓴다

## 빠른 설치

준비물
- Claude Code
- Git
- Python 3.11+

### 방법 A — AI에게 설치시키기

프로젝트 루트에서 AI에게 아래 문구를 그대로 주면 된다.
중간 확인 질문 없이 한 번에 설치시키는 용도다.
목표는 **전역 설치가 아니라 현재 프로젝트 내부 설치**고, 설치 직후 Claude에서 `/flow-init`가 보이게 만드는 것이다.

```text
현재 프로젝트 루트를 기준으로 so2x-system을 설치해줘. 중간 확인 질문 없이 한국어로 진행하고, 새 설계 문서나 task 문서는 만들지 마.
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

설치가 끝나면 프로젝트에 아래 두 축이 생긴다.

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
    ├── commands/
    ├── docs/
    ├── scripts/
    ├── src/
    ├── tasks/
    ├── signals/
    ├── candidates/
    ├── outputs/
    └── state/
```

- `.claude/commands/`는 Claude slash command surface다.
- `.so2x-system/`는 실제 실행 로직과 상태를 담는 로컬 scaffold다.
- 즉, **Claude에서는 `/flow-init`로 진입하고, 실제 실행은 `.so2x-system/scripts/execute.py`가 맡는다.**

## 실행 예시

Claude에서는:
```text
/flow-init
/flow-feature 결제 기능 첫 slice 구현
/flow-qa 로그인 실패 재현부터 잡기
```

직접 실행도 가능하다:
```bash
python3 .so2x-system/scripts/execute.py flow-init --title "Initialize project workflow"
python3 .so2x-system/scripts/execute.py flow-feature --title "Add rule promotion" --goal "Turn repeated patterns into candidates"
python3 .so2x-system/scripts/execute.py flow-qa --title "Fix failing browser proof" --goal "Capture QA misses" --pattern "browser verification missing"
python3 .so2x-system/scripts/execute.py self-improve --title "Promote recurring failures"
```

## 테스트

```bash
pytest -q
```

## 다음 단계

다음 단계: /flow-init으로 프로젝트를 초기화하세요.
