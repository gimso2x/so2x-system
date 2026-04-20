from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
TASK_DIR = ROOT / "tasks"
OUTPUT_RUN_DIR = ROOT / "outputs" / "runs"
SIGNAL_DIR = ROOT / "signals"
STATE_DIR = ROOT / "state"
CANDIDATE_DIR = ROOT / "candidates"

MODE_TO_BUCKET = {
    "flow-feature": "feature",
    "flow-qa": "qa",
    "flow-review": "review",
    "flow-init": "feature",
    "self-improve": "review",
}

TASK_TEMPLATE_KEYS = {
    "flow-feature": "feature",
    "flow-init": "feature",
    "flow-qa": "qa",
    "flow-review": "review",
    "self-improve": "self_improve",
}

SIGNAL_TYPES = {
    "flow-feature": "feature_run",
    "flow-init": "feature_run",
    "flow-qa": "qa_failure",
    "flow-review": "review_note",
}


@dataclass
class RunArtifacts:
    task_doc: Path
    run_output: Path
    signal_output: Path | None
    candidate_outputs: list[Path]


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "task"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def ensure_layout() -> None:
    directories = [
        CONFIG_DIR,
        TASK_DIR / "feature",
        TASK_DIR / "qa",
        TASK_DIR / "review",
        OUTPUT_RUN_DIR,
        SIGNAL_DIR / "fixes",
        SIGNAL_DIR / "qa-failures",
        SIGNAL_DIR / "review-notes",
        SIGNAL_DIR / "repeated-patterns",
        CANDIDATE_DIR / "rules",
        CANDIDATE_DIR / "skills",
        STATE_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    write_json_if_missing(STATE_DIR / "index.json", {"latest_task_by_mode": {}})
    write_json_if_missing(
        STATE_DIR / "metrics.json",
        {"runs_by_mode": {}, "signals_by_type": {}, "patterns": {}},
    )
    history_path = STATE_DIR / "history.jsonl"
    if not history_path.exists():
        history_path.write_text("")


def write_json_if_missing(path: Path, payload: dict[str, Any]) -> None:
    if not path.exists():
        write_json(path, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="so2x-system runner")
    parser.add_argument("mode", choices=["flow-init", "flow-feature", "flow-qa", "flow-review", "self-improve"])
    parser.add_argument("--title", required=True)
    parser.add_argument("--goal", default="")
    parser.add_argument("--scope", default="")
    parser.add_argument("--files", default="")
    parser.add_argument("--verification", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--pattern", default="")
    return parser.parse_args()


def next_task_id() -> str:
    history_path = STATE_DIR / "history.jsonl"
    count = sum(1 for line in history_path.read_text().splitlines() if line.strip()) if history_path.exists() else 0
    return f"task-{count + 1:03d}"


def task_doc_metadata(args: argparse.Namespace, task_id: str) -> dict[str, str]:
    return {
        "task_id": task_id,
        "mode": args.mode,
        "title": args.title,
        "goal": args.goal,
        "scope": args.scope,
        "files": args.files,
        "verification": args.verification,
        "notes": args.notes,
        "pattern": args.pattern,
        "created_at": iso_now(),
    }


def render_task_doc(template_key: str, metadata: dict[str, str], templates: dict[str, Any], routing: dict[str, Any]) -> str:
    template = templates[template_key]
    flow = routing.get(template["flow_key"], {}).get("flow", [])
    lines = [
        f"# {metadata['title']}",
        "",
        f"- task_id: {metadata['task_id']}",
        f"- mode: {metadata['mode']}",
        f"- created_at: {metadata['created_at']}",
        f"- route: {', '.join(flow) if flow else 'n/a'}",
        "",
    ]
    for section in template["sections"]:
        lines.append(f"## {section['title']}")
        value = metadata.get(section["key"], "").strip()
        lines.append(value or section["placeholder"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_task_doc(args: argparse.Namespace, templates: dict[str, Any], routing: dict[str, Any]) -> tuple[str, Path]:
    task_id = next_task_id()
    metadata = task_doc_metadata(args, task_id)
    task_bucket = MODE_TO_BUCKET[args.mode]
    template_key = TASK_TEMPLATE_KEYS[args.mode]
    filename = f"{task_id}-{slugify(args.title)}.md"
    task_path = TASK_DIR / task_bucket / filename
    task_path.write_text(render_task_doc(template_key, metadata, templates, routing))
    return task_id, task_path


def build_run_summary(task_id: str, args: argparse.Namespace, task_path: Path, routing: dict[str, Any]) -> dict[str, Any]:
    route = routing.get(TASK_TEMPLATE_KEYS[args.mode], {}).get("flow", [])
    return {
        "task_id": task_id,
        "mode": args.mode,
        "title": args.title,
        "goal": args.goal,
        "route": route,
        "task_doc": str(task_path.relative_to(ROOT)),
        "status": "recorded",
        "created_at": iso_now(),
        "verification": args.verification or "not-provided",
        "notes": args.notes,
    }


def signal_dir_for_mode(mode: str) -> Path:
    if mode == "flow-qa":
        return SIGNAL_DIR / "qa-failures"
    if mode == "flow-review":
        return SIGNAL_DIR / "review-notes"
    return SIGNAL_DIR / "fixes"


def create_signal(task_id: str, args: argparse.Namespace) -> dict[str, Any]:
    signal_type = SIGNAL_TYPES.get(args.mode)
    if signal_type is None:
        return {}
    return {
        "task_id": task_id,
        "type": signal_type,
        "pattern": args.pattern or args.title.lower(),
        "source": args.mode,
        "count": 1,
        "first_seen": iso_now(),
        "last_seen": iso_now(),
        "notes": args.notes,
    }


def append_history(entry: dict[str, Any]) -> None:
    history_path = STATE_DIR / "history.jsonl"
    with history_path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def update_state(task_path: Path, mode_bucket: str, signal: dict[str, Any]) -> None:
    index_path = STATE_DIR / "index.json"
    metrics_path = STATE_DIR / "metrics.json"

    index = load_json(index_path, {"latest_task_by_mode": {}})
    index["latest_task_by_mode"][mode_bucket] = str(task_path.relative_to(ROOT))
    write_json(index_path, index)

    metrics = load_json(metrics_path, {"runs_by_mode": {}, "signals_by_type": {}, "patterns": {}})
    metrics["runs_by_mode"][mode_bucket] = metrics["runs_by_mode"].get(mode_bucket, 0) + 1
    if signal:
        metrics["signals_by_type"][signal["type"]] = metrics["signals_by_type"].get(signal["type"], 0) + 1
        metrics["patterns"][signal["pattern"]] = metrics["patterns"].get(signal["pattern"], 0) + 1
    write_json(metrics_path, metrics)


def collect_pattern_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in SIGNAL_DIR.rglob("*.json"):
        data = json.loads(path.read_text())
        pattern = data.get("pattern")
        if pattern:
            counts[pattern] += 1
    return counts


def candidate_label(count: int) -> str:
    if count >= 3:
        return "candidate hard gate"
    if count == 2:
        return "candidate soft rule"
    return "record only"


def candidate_location(count: int) -> str:
    return "config/gates.yaml" if count >= 3 else "docs/RULES.md"


def write_candidate(pattern: str, count: int) -> Path:
    bucket = "rules" if count >= 2 else "skills"
    path = CANDIDATE_DIR / bucket / f"{slugify(pattern)}.md"
    content = (
        f"# {pattern}\n\n"
        f"- occurrences: {count}\n"
        f"- recommendation: {candidate_label(count)}\n"
        f"- proposed_location: {candidate_location(count)}\n"
        f"- approval_required: yes\n\n"
        "## Evidence\n"
        "Repeated pattern observed in structured signals.\n\n"
        "## Proposed change\n"
        "Promote the pattern into an explicit rule, skill, or gate after review.\n"
    )
    path.write_text(content)
    return path


def run_standard(args: argparse.Namespace, templates: dict[str, Any], routing: dict[str, Any]) -> RunArtifacts:
    task_id, task_path = write_task_doc(args, templates, routing)
    mode_bucket = MODE_TO_BUCKET[args.mode]
    run_summary = build_run_summary(task_id, args, task_path, routing)
    run_output = OUTPUT_RUN_DIR / f"{task_path.stem}.json"
    write_json(run_output, run_summary)

    signal = create_signal(task_id, args)
    signal_output = None
    if signal:
        signal_output = signal_dir_for_mode(args.mode) / f"{task_path.stem}.json"
        write_json(signal_output, signal)

    append_history(run_summary)
    update_state(task_path, mode_bucket, signal)
    return RunArtifacts(task_doc=task_path, run_output=run_output, signal_output=signal_output, candidate_outputs=[])


def run_self_improve(args: argparse.Namespace, templates: dict[str, Any], routing: dict[str, Any]) -> RunArtifacts:
    task_id, task_path = write_task_doc(args, templates, routing)
    counts = collect_pattern_counts()
    candidates = [write_candidate(pattern, count) for pattern, count in sorted(counts.items()) if count >= 2]
    run_output = OUTPUT_RUN_DIR / f"{task_path.stem}.json"
    payload = {
        "task_id": task_id,
        "mode": args.mode,
        "title": args.title,
        "generated_candidates": [str(path.relative_to(ROOT)) for path in candidates],
        "created_at": iso_now(),
    }
    write_json(run_output, payload)
    append_history(payload)
    update_state(task_path, MODE_TO_BUCKET[args.mode], {})
    return RunArtifacts(task_doc=task_path, run_output=run_output, signal_output=None, candidate_outputs=candidates)


def load_configs() -> tuple[dict[str, Any], dict[str, Any]]:
    routing = load_yaml(CONFIG_DIR / "routing.yaml")
    templates = load_yaml(CONFIG_DIR / "templates.yaml")
    _ = load_yaml(CONFIG_DIR / "evolution.yaml")
    _ = load_yaml(CONFIG_DIR / "gates.yaml")
    return routing, templates


def main() -> int:
    ensure_layout()
    args = parse_args()
    routing, templates = load_configs()
    artifacts = run_self_improve(args, templates, routing) if args.mode == "self-improve" else run_standard(args, templates, routing)
    response = {
        "task_doc": str(artifacts.task_doc.relative_to(ROOT)),
        "run_output": str(artifacts.run_output.relative_to(ROOT)),
        "signal_output": str(artifacts.signal_output.relative_to(ROOT)) if artifacts.signal_output else None,
        "candidate_outputs": [str(path.relative_to(ROOT)) for path in artifacts.candidate_outputs],
    }
    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
