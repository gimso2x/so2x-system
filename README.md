# so2x-system

so2x-system은 so2x-flow처럼 **각 프로젝트에 로컬 설치해서 쓰는 얇은 시스템 스캐폴드**다.
전역 설치가 아니라 현재 프로젝트 내부 설치를 기본으로 본다.

핵심은 간단하다.
- task 문서를 먼저 만든다
- feature/qa/review/self-improve 흐름을 라우팅한다
- run output / signal / state를 남긴다
- 반복 패턴을 rule/skill/gate 후보로 승격한다

## 빠른 설치

준비물
- Claude Code 또는 비슷한 AI 코딩 에이전트
- Git
- Python 3.11+

### 방법 A — AI에게 설치시키기

프로젝트 루트에서 AI에게 아래 문구를 그대로 주면 된다.
중간 확인 질문 없이 한 번에 설치시키는 용도다.
목표는 **전역 설치가 아니라 현재 프로젝트 내부 설치**다.

```text
현재 프로젝트 루트를 기준으로 so2x-system을 설치해줘. 중간 확인 질문 없이 한국어로 진행하고, 새 설계 문서나 task 문서는 만들지 마.
중간 단계 성공만 보고하고 응답을 끝내지 말고, 아래 1~6단계를 한 턴에서 끝까지 실제로 실행한 뒤 마지막에만 결과를 짧게 정리해.
recap이나 "다음으로 ~ 하면 됩니다" 같은 안내만 남기지 말고, 실제 실행이 남아 있으면 계속 진행해.

1. `mkdir -p .tmp .so2x-system` 를 실행해.
2. `git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-system.git .tmp/so2x-system` 를 실행해.
3. `cp -R .tmp/so2x-system/config .so2x-system/ && cp -R .tmp/so2x-system/commands .so2x-system/ && cp -R .tmp/so2x-system/docs .so2x-system/ && cp -R .tmp/so2x-system/scripts .so2x-system/ && cp -R .tmp/so2x-system/src .so2x-system/ && cp -R .tmp/so2x-system/tasks .so2x-system/ && cp -R .tmp/so2x-system/signals .so2x-system/ && cp -R .tmp/so2x-system/candidates .so2x-system/ && cp -R .tmp/so2x-system/outputs .so2x-system/ && cp -R .tmp/so2x-system/state .so2x-system/` 를 실행해.
4. `test -f .so2x-system/scripts/execute.py && test -f .so2x-system/config/routing.yaml && test -f .so2x-system/docs/PRD.md` 로 설치 결과를 확인해.
5. `rm -rf .tmp/so2x-system && rmdir .tmp 2>/dev/null || true` 를 실행해 정리해.
6. 마지막 한 줄에는 반드시 다음 실행 안내를 넣어. 문구는 정확히 `다음 단계: /flow-init으로 프로젝트를 초기화하세요.` 로 써.
```

### 방법 B — 셸에서 직접 설치

```bash
mkdir -p .tmp .so2x-system
git clone --single-branch --depth 1 https://github.com/gimso2x/so2x-system.git .tmp/so2x-system
cp -R .tmp/so2x-system/config .so2x-system/
cp -R .tmp/so2x-system/commands .so2x-system/
cp -R .tmp/so2x-system/docs .so2x-system/
cp -R .tmp/so2x-system/scripts .so2x-system/
cp -R .tmp/so2x-system/src .so2x-system/
cp -R .tmp/so2x-system/tasks .so2x-system/
cp -R .tmp/so2x-system/signals .so2x-system/
cp -R .tmp/so2x-system/candidates .so2x-system/
cp -R .tmp/so2x-system/outputs .so2x-system/
cp -R .tmp/so2x-system/state .so2x-system/
test -f .so2x-system/scripts/execute.py
test -f .so2x-system/config/routing.yaml
test -f .so2x-system/docs/PRD.md
rm -rf .tmp/so2x-system
rmdir .tmp 2>/dev/null || true
```

## 실행 예시

```bash
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
