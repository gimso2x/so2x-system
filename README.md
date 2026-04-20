# so2x-system

Thin orchestration and evolution layer for Superpowers-style execution.

## What it does
- creates durable task docs before execution
- routes feature/qa/review/self-improve runs through config-defined flows
- records run outputs, signals, and aggregate state
- promotes repeated patterns into candidate rules or skills

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage
```bash
so2x-system flow-feature --title "Add rule promotion" --goal "Turn repeated patterns into candidates"
so2x-system flow-qa --title "Fix failing browser proof" --goal "Capture QA misses" --pattern "browser verification missing"
so2x-system self-improve --title "Promote recurring failures"
```

## Test
```bash
pytest
```
