#!/usr/bin/env python3
"""Metering + concurrency (B4.2 part 2) — v2 §82.8 / §81 Mode S.

  * Every model call's usage is recorded into the episode package and priced
    from control/models/prices.yaml (estimated cost; provider billing is
    account-level under Mode S).
  * prices.yaml carries an `as_of` date; a staleness guard refuses to meter
    against rates older than MAX_PRICE_AGE_DAYS (owner constraint 2026-07-17)
    — stale prices make budget enforcement fiction.
  * The envelope cost ceiling (budgets.model_cost_limit_usd, optional) is
    enforced: breach → task BLOCKED (§81.3), never silently exceeded.
  * The global concurrency cap comes from policies.yaml
    mode_s.concurrency_cap — never a constant (owner constraint). Dispatches
    above the cap QUEUE (FIFO); they are not failed (§82.8).
"""
from __future__ import annotations

import datetime
import json
from collections import deque
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PRICES_PATH = REPO_ROOT / "control" / "models" / "prices.yaml"
POLICIES_PATH = REPO_ROOT / "control" / "models" / "policies.yaml"

MAX_PRICE_AGE_DAYS = 90


class MeteringError(Exception):
    pass


class BudgetExceeded(MeteringError):
    pass


def _today() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


class Meter:
    """Prices, staleness guard, per-task usage accounting."""

    def __init__(self, prices_path: Path = PRICES_PATH,
                 max_age_days: int = MAX_PRICE_AGE_DAYS):
        data = yaml.safe_load(prices_path.read_text(encoding="utf-8"))
        as_of = data.get("as_of")
        if isinstance(as_of, str):
            as_of = datetime.date.fromisoformat(as_of)
        if not isinstance(as_of, datetime.date):
            raise MeteringError("prices.yaml: as_of missing or not a date")
        age = (_today() - as_of).days
        if age > max_age_days:
            raise MeteringError(
                f"prices.yaml as_of {as_of} is {age} days old "
                f"(max {max_age_days}) — refresh rates before metering; "
                "stale prices make budget enforcement fiction"
            )
        self.as_of = as_of
        self.rates = data["models"]

    def cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float:
        if model not in self.rates:
            raise MeteringError(
                f"model {model!r} has no rate in prices.yaml — refusing to "
                "meter at an invented price"
            )
        rate = self.rates[model]
        return round(
            input_tokens * rate["input_per_mtok"] / 1_000_000
            + output_tokens * rate["output_per_mtok"] / 1_000_000,
            6,
        )

    def record_usage(self, task_dir: Path, *, model: str, input_tokens: int,
                     output_tokens: int) -> dict:
        """Append a usage line to the episode log and update usage.yaml
        totals. Returns the running totals."""
        cost = self.cost_usd(model, input_tokens, output_tokens)
        usage_path = task_dir / "usage.yaml"
        usage = (
            yaml.safe_load(usage_path.read_text()) if usage_path.exists()
            else {"total_input_tokens": 0, "total_output_tokens": 0,
                  "total_estimated_cost_usd": 0.0, "calls": 0,
                  "prices_as_of": self.as_of.isoformat()}
        )
        usage["total_input_tokens"] += input_tokens
        usage["total_output_tokens"] += output_tokens
        usage["total_estimated_cost_usd"] = round(
            usage["total_estimated_cost_usd"] + cost, 6
        )
        usage["calls"] += 1
        usage_path.write_text(
            yaml.safe_dump(usage, sort_keys=False), encoding="utf-8"
        )
        log_path = task_dir / "log.jsonl"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "at": datetime.datetime.now(datetime.timezone.utc)
                      .isoformat(timespec="seconds").replace("+00:00", "Z"),
                "event": "model_usage", "model": model,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "estimated_cost_usd": cost,
            }, sort_keys=True) + "\n")
        return usage

    def enforce_ceiling(self, task_dir: Path) -> None:
        """§81.3: envelope ceiling breach → BLOCKED (caller performs the
        transition; this raises the typed signal)."""
        task = yaml.safe_load((task_dir / "task.yaml").read_text())
        ceiling = (task.get("budgets") or {}).get("model_cost_limit_usd")
        if ceiling is None:
            return
        usage_path = task_dir / "usage.yaml"
        if not usage_path.exists():
            return
        spent = yaml.safe_load(usage_path.read_text())["total_estimated_cost_usd"]
        if spent > ceiling:
            raise BudgetExceeded(
                f"estimated cost {spent} USD exceeds envelope ceiling "
                f"{ceiling} USD — task must be BLOCKED (§81.3)"
            )


class SessionPool:
    """Global concurrent-session cap (§81.4). Cap read from policies.yaml
    mode_s.concurrency_cap at construction; dispatches above the cap queue
    FIFO rather than failing (§82.8)."""

    def __init__(self, policies_path: Path = POLICIES_PATH):
        policies = yaml.safe_load(policies_path.read_text(encoding="utf-8"))
        try:
            cap = policies["mode_s"]["concurrency_cap"]
        except (KeyError, TypeError):
            raise MeteringError(
                "policies.yaml: mode_s.concurrency_cap missing — the cap is "
                "config, never a constant"
            )
        if not isinstance(cap, int) or cap < 1:
            raise MeteringError(f"concurrency_cap must be a positive int, got {cap!r}")
        self.cap = cap
        self.active: set[str] = set()
        self.queue: deque[str] = deque()

    def request(self, task_id: str) -> bool:
        """True → slot granted, dispatch now. False → queued (FIFO)."""
        if task_id in self.active:
            return True  # idempotent: a task holds at most one slot
        if len(self.active) < self.cap:
            self.active.add(task_id)
            return True
        if task_id not in self.queue:
            self.queue.append(task_id)
        return False

    def release(self, task_id: str) -> str | None:
        """Free a slot; returns the next queued task granted a slot, if any."""
        self.active.discard(task_id)
        if self.queue and len(self.active) < self.cap:
            nxt = self.queue.popleft()
            self.active.add(nxt)
            return nxt
        return None
