#!/usr/bin/env python3
"""metrics-weekly (B6.3) — v2 §78 row 26, Phase-1 telemetry.

Computes the weekly metrics artifact from repository truth only (transcripts
and proxy usage arrive in later phases; §60–61):

  merges        merged PRs into main in the window (git, first-parent)
  reverts       revert commits on main in the window (fix-forward signal)
  gates         gate records by decision + owner; gate-rejection rate
                (CHANGES_REQUIRED + REJECTED over all decided in window)
  escalations   ESC-/INC- records created in the window
  tasks         episode packages: success (DONE), blocked, in-flight;
                latency = first→last state transition wall-clock
  cost          metered usage from episodes' usage.yaml priced against
                control/models/prices.yaml (estimates, Mode S)

Sections with no underlying data report explicitly ("no data"), never
zeros pretending to be measurements (§87e demands a real artifact, not a
fiction of one).

Usage:
  metrics_weekly.py [--until YYYY-MM-DD] [--days 7] [--out DIR] [--root DIR]

Writes <out>/METRICS-<ISOyear>-W<week>.md (artifact front matter + human
table + machine-readable yaml block). Exit 0 on success.
"""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MERGE_RE = re.compile(r"Merge pull request #(\d+)")
REJECTING = ("CHANGES_REQUIRED", "REJECTED")


def parse_date(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


def window(until: datetime.date, days: int) -> tuple[datetime.date, datetime.date]:
    return until - datetime.timedelta(days=days - 1), until


def git_log(root: Path, since: datetime.date, until: datetime.date) -> list[str]:
    out = subprocess.run(
        [
            "git", "-C", str(root), "log", "--first-parent",
            f"--since={since}T00:00:00", f"--until={until}T23:59:59",
            "--pretty=%s",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def collect_git(root: Path, since, until) -> dict:
    subjects = git_log(root, since, until)
    merged = [int(m.group(1)) for s in subjects if (m := MERGE_RE.search(s))]
    reverts = sum(1 for s in subjects if s.startswith("Revert"))
    return {"merged_prs": sorted(set(merged)), "merge_count": len(set(merged)), "revert_count": reverts}


def collect_gates(root: Path, since, until) -> dict:
    gates_dir = root / "gates"
    decided = []
    for path in sorted(gates_dir.glob("GATE-*.yaml")) if gates_dir.is_dir() else []:
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(record, dict):
            continue
        raw = str(record.get("decided_at", ""))[:10]
        try:
            day = parse_date(raw)
        except ValueError:
            continue
        if since <= day <= until:
            decided.append(record)
    by_decision: dict[str, int] = {}
    by_owner: dict[str, int] = {}
    for r in decided:
        by_decision[r.get("decision", "?")] = by_decision.get(r.get("decision", "?"), 0) + 1
        by_owner[r.get("gate_owner", "?")] = by_owner.get(r.get("gate_owner", "?"), 0) + 1
    total = len(decided)
    rejections = sum(by_decision.get(d, 0) for d in REJECTING)
    return {
        "decided": total,
        "by_decision": by_decision,
        "by_owner": by_owner,
        "rejection_rate": (round(rejections / total, 3) if total else None),
    }


def collect_escalations(root: Path, since, until) -> dict:
    esc_dir = root / "control" / "escalations"
    counts = {"ESC": 0, "INC": 0}
    for path in sorted(esc_dir.glob("*.md")) if esc_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---", 4)
        try:
            fm = yaml.safe_load(text[4:end]) if end != -1 else None
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        try:
            day = parse_date(str(fm.get("created", ""))[:10])
        except ValueError:
            continue
        if since <= day <= until:
            kind = "INC" if path.name.startswith("INC-") else "ESC"
            counts[kind] += 1
    return counts


def _load_prices(root: Path) -> dict:
    path = root / "control" / "models" / "prices.yaml"
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("models") or {}


def collect_tasks(root: Path, since, until) -> dict:
    episodes = root / "episodes"
    if not episodes.is_dir():
        return {"packages": 0, "note": "no episode packages (idle-by-design during bootstrap)"}
    prices = _load_prices(root)
    done = blocked = in_flight = 0
    latencies: list[float] = []
    cost = 0.0
    tokens_in = tokens_out = 0
    for task_dir in sorted(p for p in episodes.iterdir() if p.is_dir() and p.name.startswith("TASK-")):
        state_path = task_dir / "state.yaml"
        if not state_path.is_file():
            continue
        state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        history = state.get("history") or []
        stamps = []
        for entry in history:
            try:
                stamps.append(
                    datetime.datetime.fromisoformat(str(entry.get("at", "")).replace("Z", "+00:00"))
                )
            except ValueError:
                continue
        if stamps and not (since <= stamps[-1].date() <= until):
            continue
        status = str(state.get("status", "")).upper()
        if status == "DONE":
            done += 1
        elif status == "BLOCKED":
            blocked += 1
        else:
            in_flight += 1
        if len(stamps) >= 2:
            latencies.append((max(stamps) - min(stamps)).total_seconds() / 60)
        usage_path = task_dir / "usage.yaml"
        if usage_path.is_file():
            usage = yaml.safe_load(usage_path.read_text(encoding="utf-8")) or {}
            for call in usage.get("calls") or []:
                model = prices.get(str(call.get("model", "")), {})
                t_in = int(call.get("input_tokens", 0))
                t_out = int(call.get("output_tokens", 0))
                tokens_in += t_in
                tokens_out += t_out
                cost += t_in / 1e6 * float(model.get("input_per_mtok", 0.0))
                cost += t_out / 1e6 * float(model.get("output_per_mtok", 0.0))
    closed = done + blocked
    return {
        "packages": done + blocked + in_flight,
        "done": done,
        "blocked": blocked,
        "in_flight": in_flight,
        "success_rate": (round(done / closed, 3) if closed else None),
        "latency_minutes_median": (round(sorted(latencies)[len(latencies) // 2], 1) if latencies else None),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "estimated_cost_usd": round(cost, 4),
    }


def build_metrics(root: Path, until: datetime.date, days: int) -> dict:
    since, until = window(until, days)
    return {
        "window": {"since": str(since), "until": str(until), "days": days},
        "git": collect_git(root, since, until),
        "gates": collect_gates(root, since, until),
        "escalations": collect_escalations(root, since, until),
        "tasks": collect_tasks(root, since, until),
    }


def render(metrics: dict, until: datetime.date) -> str:
    iso = until.isocalendar()
    week_id = f"{iso.year}-W{iso.week:02d}"
    g, ga, e, t = metrics["git"], metrics["gates"], metrics["escalations"], metrics["tasks"]
    today = str(until)
    rejection = ga["rejection_rate"]
    success = t.get("success_rate")
    latency = t.get("latency_minutes_median")
    lines = [
        "---",
        f"artifact_id: METRICS-{week_id}",
        f"title: Weekly metrics {week_id} (v2 \u00a778 row 26)",
        "type: metrics-report",
        "project: company",
        "owner: bootstrap agent (agenticfoundrybot)",
        'version: "1.0"',
        "status: APPROVED",
        "sensitivity: internal",
        f'created: "{today}"',
        f'updated: "{today}"',
        "---",
        "",
        f"# Weekly Metrics — {week_id}",
        "",
        f"Window {metrics['window']['since']} → {metrics['window']['until']} "
        f"({metrics['window']['days']} days). Sources: git history, gates/, "
        "control/escalations/, episodes/ (v2 \u00a760\u201361 Phase-1 scope).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Merged PRs (main, first-parent) | {g['merge_count']} ({', '.join('#' + str(n) for n in g['merged_prs']) or 'none'}) |",
        f"| Revert commits | {g['revert_count']} |",
        f"| Gate records decided | {ga['decided']} |",
        f"| Gate decisions | {ga['by_decision'] or 'none'} |",
        f"| Gate owners | {ga['by_owner'] or 'none'} |",
        f"| Gate-rejection rate | {'no decided gates' if rejection is None else rejection} |",
        f"| Escalations opened (ESC / INC) | {e['ESC']} / {e['INC']} |",
        f"| Episode packages in window | {t['packages']}{' — ' + t['note'] if 'note' in t else ''} |",
        f"| Task success rate | {'no closed tasks' if success is None else success} |",
        f"| Task latency median (min) | {'no data' if latency is None else latency} |",
        f"| Metered tokens (in/out) | {t.get('tokens_input', 0)} / {t.get('tokens_output', 0)} |",
        f"| Estimated cost (USD, Mode S) | {t.get('estimated_cost_usd', 0.0)} |",
        "",
        "```yaml",
        yaml.safe_dump(metrics, sort_keys=False).rstrip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Weekly metrics (v2 \u00a778 row 26)")
    ap.add_argument("--until", type=parse_date, default=datetime.date.today())
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", help="output dir (default company/metrics)")
    ap.add_argument("--root", help="repo root (testing)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve() if args.root else REPO_ROOT

    metrics = build_metrics(root, args.until, args.days)
    report = render(metrics, args.until)
    out_dir = Path(args.out) if args.out else root / "company" / "metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    iso = args.until.isocalendar()
    out_path = out_dir / f"METRICS-{iso.year}-W{iso.week:02d}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"metrics-weekly: wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
