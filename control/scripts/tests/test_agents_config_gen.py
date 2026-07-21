"""Tests for agents_config_gen.py — the snippet must mirror policies.yaml
exactly (MODEL-001/002 by construction) and carry the provenance header
(the only drift defense for host config; owner answer 4, 2026-07-21)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import agents_config_gen as acg  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
REAL_POLICIES = REPO / "control" / "models" / "policies.yaml"

ROLE_CODES = ["PJM", "SAA", "UUD", "SDE", "SAT", "SSE", "DPC",
              "DCE", "DE", "AIE", "TW", "ALE", "LIN"]


def strip_comments(text: str) -> str:
    return "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith("//")
    )


def test_real_policies_render_13_agents_in_order():
    text = acg.generate(REAL_POLICIES, commit="abc1234", today="2026-07-21")
    doc = json.loads(strip_comments(text))
    entries = doc["agents"]["list"]
    assert [e["id"] for e in entries] == [c.lower() for c in ROLE_CODES]

    policies = yaml.safe_load(REAL_POLICIES.read_text(encoding="utf-8"))
    for entry in entries:
        code = entry["id"].upper()
        pol = policies["policies"][policies["agents"][code]]
        assert entry["model"]["primary"] == pol["primary"]
        assert entry["model"]["fallbacks"] == [pol["fallback"]]
        assert entry["workspace"] == f"~/company-agents/{entry['id']}"


def test_model_001_family_decorrelation_survives_generation():
    """SAT (reviewer) must sit in a different model family than SDE
    (implementer) in BOTH slots — decorrelation holds during fallback
    windows (MODEL-001; policies.yaml comment)."""
    text = acg.generate(REAL_POLICIES, commit="abc1234", today="2026-07-21")
    entries = {e["id"]: e for e in json.loads(strip_comments(text))["agents"]["list"]}

    def family(model_ref):
        return model_ref.split("/", 1)[0]

    sat, sde = entries["sat"], entries["sde"]
    assert family(sat["model"]["primary"]) != family(sde["model"]["primary"])
    # SAT's fallback stays in SAT's own family (standard = same family both slots)
    assert family(sat["model"]["fallbacks"][0]) == family(sat["model"]["primary"])


def test_provenance_header_present_and_body_parses():
    text = acg.generate(REAL_POLICIES, commit="deadbee", today="2026-07-21")
    head = "\n".join(text.splitlines()[:8])
    assert "DO NOT HAND-EDIT" in head
    assert "control/models/policies.yaml @ deadbee" in head
    assert "generated: 2026-07-21" in head
    assert "regenerate after ANY policies.yaml change" in head
    assert "STRICT" in head  # explains why fallbacks are explicit
    json.loads(strip_comments(text))  # JSON5-with-comments → valid JSON body


def test_missing_policy_reference_fails_loudly(tmp_path):
    bad = tmp_path / "p.yaml"
    bad.write_text("policies: {}\nagents: {SDE: reasoning-max}\n")
    with pytest.raises(acg.ConfigGenError, match="SDE"):
        acg.generate(bad, commit="x", today="2026-07-21")


def test_main_writes_out_file(tmp_path, capsys):
    out = tmp_path / "agents.json5"
    rc = acg.main(["--policies", str(REAL_POLICIES), "--commit", "abc1234",
                   "--out", str(out)])
    assert rc == 0
    assert "wrote" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8").startswith("// GENERATED")
