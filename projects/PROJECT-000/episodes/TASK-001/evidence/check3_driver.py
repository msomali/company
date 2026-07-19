#!/usr/bin/env python3
"""§88 check 3 driver — dispatch prompt contract via recorded-prompt backend
(Gate 0 P2 decision, option b; owner 2026-07-18).

What this does, in order:
1. REAL-REPO REFUSAL PROOF: runs Dispatcher.dispatch() against the real repo
   (recording backend, null committer). Expected: DispatchError because
   control/manifests/sde.yaml is 'contract-only' — no manifest is activated
   during the dry run (BA-2.4).
2. SCRATCH-WORLD DISPATCH: copies schemas/manifests/digest/TASK-001 into a
   temp dir, flips the *copy* of sde.yaml to status: active (simulating the
   post-§88 human act, exactly as test_dispatch_happy_path_when_active does),
   runs dispatch(), and captures the actual generated prompt.
3. CONTRACT ASSERTIONS on the captured prompt (§88.3 / v1 §48.2):
   - digest present inline (T2) — first line of company/digest-v1.1.md
   - task envelope embedded as yaml (task_id, acceptance_criteria, budgets)
   - artifact-links section renders when inputs exist (TASK-001 has no
     inputs, so this is proven on an inputs-bearing variant, second capture)
4. Writes prompt captures + a result summary next to itself under evidence/.

No real manifest is modified; no model is called; the recording backend only
stores the prompt and returns a synthetic run id.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import yaml

EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[4]
sys.path.insert(0, str(REPO_ROOT / "control" / "scripts"))
import dispatcher as dp  # noqa: E402


class RecordingBackend:
    """P2 option (b): records the prompt; spawns nothing."""

    def __init__(self):
        self.spawned = []

    def spawn(self, agent_id, prompt):
        self.spawned.append((agent_id, prompt))
        return f"recorded-run-{len(self.spawned):03d}"


class NullCommitter:
    def __init__(self):
        self.commits = []

    def commit(self, paths, message):
        self.commits.append(([str(p) for p in paths], message))


def main() -> int:
    results = []

    # 1. Real-repo refusal (proves no activation happened in the repo).
    real = dp.Dispatcher(
        repo_root=REPO_ROOT, backend=RecordingBackend(), committer=NullCommitter()
    )
    try:
        real.dispatch("PROJECT-000", "TASK-001")
        results.append(("real-repo refusal", "FAIL — dispatch unexpectedly succeeded"))
        return 1
    except dp.DispatchError as exc:
        ok = "not 'active'" in str(exc)
        results.append(
            ("real-repo refusal",
             f"{'PASS' if ok else 'FAIL'} — DispatchError: {exc}")
        )
        if not ok:
            return 1
    assert real.backend.spawned == [], "refusal must precede any spawn"

    # 2. Scratch world.
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        (scratch / "control").mkdir()
        shutil.copytree(REPO_ROOT / "control/schemas", scratch / "control/schemas")
        shutil.copytree(REPO_ROOT / "control/manifests", scratch / "control/manifests")
        (scratch / "company").mkdir()
        shutil.copy(REPO_ROOT / "company/digest-v1.1.md", scratch / "company/digest-v1.1.md")
        task_src = REPO_ROOT / "projects/PROJECT-000/episodes/TASK-001"
        task_dst = scratch / "projects/PROJECT-000/episodes/TASK-001"
        task_dst.mkdir(parents=True)
        for name in ("task.yaml", "state.yaml"):
            shutil.copy(task_src / name, task_dst / name)

        sde = scratch / "control/manifests/sde.yaml"
        m = yaml.safe_load(sde.read_text())
        m["status"] = "active"  # scratch copy only — simulated post-§88 act
        sde.write_text(yaml.safe_dump(m, sort_keys=False))

        backend = RecordingBackend()
        d = dp.Dispatcher(
            repo_root=scratch, backend=backend, committer=NullCommitter()
        )
        run_id = d.dispatch("PROJECT-000", "TASK-001")
        agent_id, prompt = backend.spawned[0]
        results.append(("scratch dispatch",
                        f"PASS — run_id={run_id}, agent_id={agent_id}"))

        # 3. Contract assertions.
        digest_first_line = (
            (REPO_ROOT / "company/digest-v1.1.md").read_text().splitlines()[0]
        )
        envelope = yaml.safe_load((task_src / "task.yaml").read_text())
        checks = {
            "digest inline (T2)": digest_first_line in prompt,
            "envelope yaml block": "## Task envelope" in prompt
            and "task_id: TASK-001" in prompt
            and "acceptance_criteria:" in prompt
            and "model_cost_limit_usd: 5.0" in prompt,
            "envelope fields verbatim": all(
                str(c) in prompt for c in envelope["acceptance_criteria"]
            ),
        }
        for name, ok in checks.items():
            results.append((name, "PASS" if ok else "FAIL"))
        (EVIDENCE_DIR / "check3-dispatch-prompt.txt").write_text(prompt)

        # Artifact-links leg: TASK-001 carries no inputs, so build_prompt is
        # exercised on an inputs-bearing variant (contract §48.2 links leg).
        variant = dict(envelope, inputs=[
            {"artifact_id": "projects/PROJECT-000/charter.md"}
        ])
        vprompt = d.build_prompt(variant)
        ok = ("## Input artifacts" in vprompt
              and "- projects/PROJECT-000/charter.md" in vprompt)
        results.append(("artifact links render (inputs variant)",
                        "PASS" if ok else "FAIL"))
        (EVIDENCE_DIR / "check3-dispatch-prompt-inputs-variant.txt").write_text(vprompt)

        # Scratch state/log side effects (recorded for completeness).
        sstate = yaml.safe_load((task_dst / "state.yaml").read_text())
        results.append(("scratch run_id recorded",
                        "PASS" if sstate.get("run_id") == run_id else "FAIL"))
        results.append(("scratch log.jsonl written",
                        "PASS" if (task_dst / "log.jsonl").exists() else "FAIL"))

    summary = "\n".join(f"{name}: {verdict}" for name, verdict in results)
    (EVIDENCE_DIR / "check3-results.txt").write_text(summary + "\n")
    print(summary)
    return 0 if all(v.startswith("PASS") for _, v in results) else 1


if __name__ == "__main__":
    sys.exit(main())
