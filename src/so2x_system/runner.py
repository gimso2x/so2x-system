from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from so2x_system.adapters.superpowers import run_superpowers_skill

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
    exit_code: int = 0


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


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def write_json_if_missing(path: Path, payload: Any) -> None:
    if not path.exists():
        write_json(path, payload)


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
    write_json_if_missing(STATE_DIR / "approved_rules.json", [])
    history_path = STATE_DIR / "history.jsonl"
    if not history_path.exists():
        history_path.write_text("")


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


def route_steps_for_mode(routing: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    return routing.get(TASK_TEMPLATE_KEYS[mode], {}).get("flow", [])


def route_targets(steps: list[dict[str, Any]]) -> list[str]:
    return [step.get("target", step.get("id", "unknown")) for step in steps]


def build_dispatch_plan(args: argparse.Namespace, routing: dict[str, Any], task_doc: Path) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for step in route_steps_for_mode(routing, args.mode):
        plan.append(
            {
                "step_id": step["id"],
                "kind": step["kind"],
                "target": step["target"],
                "input": {
                    "task_doc": str(task_doc.relative_to(ROOT)),
                    "mode": args.mode,
                    "verification": args.verification or "not-provided",
                },
            }
        )
    return plan


def render_task_doc(template_key: str, metadata: dict[str, str], templates: dict[str, Any], routing: dict[str, Any]) -> str:
    template = templates[template_key]
    flow = route_targets(route_steps_for_mode(routing, metadata["mode"]))
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


def build_run_summary(
    task_id: str,
    args: argparse.Namespace,
    task_path: Path,
    dispatch_plan: list[dict[str, Any]],
    approved_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "mode": args.mode,
        "title": args.title,
        "goal": args.goal,
        "dispatch_plan": dispatch_plan,
        "task_doc": str(task_path.relative_to(ROOT)),
        "status": "recorded",
        "created_at": iso_now(),
        "verification": args.verification or "not-provided",
        "notes": args.notes,
        "approved_rules": approved_rules,
    }


def signal_dir_for_mode(mode: str) -> Path:
    if mode == "flow-qa":
        return SIGNAL_DIR / "qa-failures"
    if mode == "flow-review":
        return SIGNAL_DIR / "review-notes"
    return SIGNAL_DIR / "fixes"


def gate_requires_browser_proof(args: argparse.Namespace, gate_cfg: dict[str, Any]) -> bool:
    files_text = (args.files or "").lower()
    verification_text = (args.verification or "").lower()
    ui_file_hints = [hint.lower() for hint in gate_cfg.get("ui_file_hints", [])]
    verification_hints = [hint.lower() for hint in gate_cfg.get("verification_hints", [])]
    has_ui_file_signal = any(hint in files_text for hint in ui_file_hints)
    has_browser_proof = any(hint in verification_text for hint in verification_hints)
    return has_ui_file_signal and not has_browser_proof


def create_signal(task_id: str, args: argparse.Namespace, dispatch_results: list[dict[str, Any]] | None = None, signal_type: str | None = None, pattern: str | None = None, notes: str | None = None) -> dict[str, Any]:
    resolved_type = signal_type or SIGNAL_TYPES.get(args.mode)
    if resolved_type is None:
        return {}

    verification_text = (args.verification or "").lower()
    files_text = (args.files or "").lower()
    goal_text = f"{args.title} {args.goal} {args.scope}".lower()
    resolved_pattern = pattern or args.pattern or args.title.lower()
    resolved_notes = notes if notes is not None else args.notes

    ui_file_hints = (".tsx", ".jsx", "app/", "components/", "pages/", "public/")
    verification_hints = ("browser", "playwright", "snapshot", "qa")
    if args.mode in {"flow-feature", "flow-init"} and any(hint in files_text for hint in ui_file_hints) and not any(hint in verification_text for hint in verification_hints):
        resolved_pattern = "browser verification missing"
        resolved_notes = "UI-oriented work ran without browser proof in verification context"
    elif args.mode == "flow-review" and dispatch_results:
        failed_reviews = [step for step in dispatch_results if step.get("status") == "failed"]
        if failed_reviews:
            resolved_pattern = "repeated_review_issue"
            resolved_notes = failed_reviews[0].get("stderr", "Review flow reported a repeated issue")
    elif args.mode == "flow-qa" and "env" in goal_text and "dispatch_failure" == resolved_type:
        resolved_pattern = "environment_instability"

    return {
        "task_id": task_id,
        "type": resolved_type,
        "pattern": resolved_pattern,
        "source": args.mode,
        "count": 1,
        "first_seen": iso_now(),
        "last_seen": iso_now(),
        "notes": resolved_notes,
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
        f"pattern: {pattern}\n"
        f"approved: false\n"
        f"occurrences: {count}\n"
        f"recommendation: {candidate_label(count)}\n"
        f"proposed_location: {candidate_location(count)}\n"
        f"approval_required: yes\n\n"
        "## Evidence\n"
        "Repeated pattern observed in structured signals.\n\n"
        "## Proposed change\n"
        "Promote the pattern into an explicit rule, skill, or gate after review.\n"
    )
    path.write_text(content)
    return path


def parse_candidate_rule(path: Path) -> dict[str, Any] | None:
    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if ": " in line and not line.startswith("#"):
            key, value = line.split(": ", 1)
            metadata[key.strip()] = value.strip()
    if metadata.get("approved") != "true":
        return None
    return {
        "pattern": metadata.get("pattern", path.stem.replace("-", " ")),
        "recommendation": metadata.get("recommendation", "candidate soft rule"),
        "proposed_location": metadata.get("proposed_location", "docs/RULES.md"),
        "source": str(path.relative_to(ROOT)),
    }


def sync_approved_rules() -> list[dict[str, Any]]:
    approved_rules = [
        rule
        for path in sorted((CANDIDATE_DIR / "rules").glob("*.md"))
        if (rule := parse_candidate_rule(path)) is not None
    ]
    write_json(STATE_DIR / "approved_rules.json", approved_rules)
    return approved_rules


def gate_blockers(args: argparse.Namespace, gates: dict[str, Any], approved_rules: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for gate_name, gate_cfg in gates.get("gates", {}).items():
        enabled = bool(gate_cfg.get("enabled")) or any(rule["pattern"] == gate_cfg.get("pattern") for rule in approved_rules)
        if not enabled:
            continue
        action = gate_cfg.get("action")
        if action == "require_browser_proof_for_ui_changes" and gate_requires_browser_proof(args, gate_cfg):
            blockers.append(gate_name)
    return blockers


def run_internal_step(step: dict[str, Any], args: argparse.Namespace, task_doc: Path, approved_rules: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "step_id": step["step_id"],
        "kind": "internal",
        "target": step["target"],
        "input": step["input"],
        "status": "success",
        "summary": "local internal step recorded",
        "artifacts": [],
        "next_steps": [],
        "prompt": (
            f"internal_step: {step['target']}\n"
            f"mode: {args.mode}\n"
            f"task_doc: {task_doc}\n"
            f"approved_rules: {len(approved_rules)}\n"
        ),
    }


def dispatch_flow(args: argparse.Namespace, dispatch_plan: list[dict[str, Any]], task_doc: Path, approved_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for step in dispatch_plan:
        if step.get("kind") == "internal":
            results.append(run_internal_step(step, args, task_doc, approved_rules))
            continue
        result = run_superpowers_skill(
            {"id": step["step_id"], "target": step["target"]},
            mode=args.mode,
            title=args.title,
            goal=args.goal,
            verification=args.verification,
            task_doc=task_doc,
            approved_rules=approved_rules,
            cwd=ROOT,
        )
        result["input"] = step["input"]
        results.append(result)
        if results[-1].get("status") == "failed":
            break
    return results


def write_signal_file(args: argparse.Namespace, task_path: Path, signal: dict[str, Any]) -> Path | None:
    if not signal:
        return None
    signal_output = signal_dir_for_mode(args.mode) / f"{task_path.stem}.json"
    write_json(signal_output, signal)
    return signal_output


def run_standard(args: argparse.Namespace, templates: dict[str, Any], routing: dict[str, Any], gates: dict[str, Any]) -> RunArtifacts:
    approved_rules = sync_approved_rules()
    task_id, task_path = write_task_doc(args, templates, routing)
    dispatch_plan = build_dispatch_plan(args, routing, task_path)
    mode_bucket = MODE_TO_BUCKET[args.mode]
    run_summary = build_run_summary(task_id, args, task_path, dispatch_plan, approved_rules)
    run_output = OUTPUT_RUN_DIR / f"{task_path.stem}.json"

    blockers = gate_blockers(args, gates, approved_rules)
    gate_results = {
        "status": "blocked" if blockers else "passed",
        "blockers": blockers,
    }
    if blockers:
        run_summary.update({"status": "blocked", "gate_results": gate_results, "dispatch_results": []})
        write_json(run_output, run_summary)
        signal = create_signal(task_id, args, signal_type="gate_block", pattern=blockers[0], notes="Blocked by approved gate")
        signal_output = write_signal_file(args, task_path, signal)
        append_history(run_summary)
        update_state(task_path, mode_bucket, signal)
        return RunArtifacts(task_doc=task_path, run_output=run_output, signal_output=signal_output, candidate_outputs=[], exit_code=2)

    dispatch_results = dispatch_flow(args, dispatch_plan, task_path, approved_rules)
    failed_steps = [step for step in dispatch_results if step.get("status") == "failed"]
    run_summary.update({
        "status": "failed" if failed_steps else "success",
        "gate_results": gate_results,
        "dispatch_results": dispatch_results,
    })
    write_json(run_output, run_summary)

    signal = create_signal(task_id, args, dispatch_results=dispatch_results)
    if failed_steps:
        signal = create_signal(
            task_id,
            args,
            dispatch_results=dispatch_results,
            signal_type="dispatch_failure",
            pattern=failed_steps[0]["target"],
            notes=failed_steps[0].get("stderr", "dispatch failed"),
        )
    signal_output = write_signal_file(args, task_path, signal)

    append_history(run_summary)
    update_state(task_path, mode_bucket, signal)
    return RunArtifacts(task_doc=task_path, run_output=run_output, signal_output=signal_output, candidate_outputs=[], exit_code=1 if failed_steps else 0)


def run_self_improve(args: argparse.Namespace, templates: dict[str, Any], routing: dict[str, Any]) -> RunArtifacts:
    task_id, task_path = write_task_doc(args, templates, routing)
    approved_rules = sync_approved_rules()
    dispatch_plan = build_dispatch_plan(args, routing, task_path)
    dispatch_results = dispatch_flow(args, dispatch_plan, task_path, approved_rules)
    counts = collect_pattern_counts()
    candidates = [write_candidate(pattern, count) for pattern, count in sorted(counts.items()) if count >= 2]
    run_output = OUTPUT_RUN_DIR / f"{task_path.stem}.json"
    payload = {
        "task_id": task_id,
        "mode": args.mode,
        "title": args.title,
        "dispatch_plan": dispatch_plan,
        "gate_results": {"status": "passed", "blockers": []},
        "dispatch_results": dispatch_results,
        "generated_candidates": [str(path.relative_to(ROOT)) for path in candidates],
        "approved_rules": approved_rules,
        "created_at": iso_now(),
    }
    write_json(run_output, payload)
    append_history(payload)
    update_state(task_path, MODE_TO_BUCKET[args.mode], {})
    return RunArtifacts(task_doc=task_path, run_output=run_output, signal_output=None, candidate_outputs=candidates)


def load_configs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    routing = load_yaml(CONFIG_DIR / "routing.yaml")
    templates = load_yaml(CONFIG_DIR / "templates.yaml")
    evolution = load_yaml(CONFIG_DIR / "evolution.yaml")
    gates = load_yaml(CONFIG_DIR / "gates.yaml")
    return routing, templates, evolution, gates


def main() -> int:
    ensure_layout()
    args = parse_args()
    routing, templates, _evolution, gates = load_configs()
    artifacts = run_self_improve(args, templates, routing) if args.mode == "self-improve" else run_standard(args, templates, routing, gates)
    response = {
        "task_doc": str(artifacts.task_doc.relative_to(ROOT)),
        "run_output": str(artifacts.run_output.relative_to(ROOT)),
        "signal_output": str(artifacts.signal_output.relative_to(ROOT)) if artifacts.signal_output else None,
        "candidate_outputs": [str(path.relative_to(ROOT)) for path in artifacts.candidate_outputs],
    }
    print(json.dumps(response))
    return artifacts.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
