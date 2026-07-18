from pathlib import Path

import handoff_check as hc

REPO = Path(__file__).resolve().parents[3]

TEMPLATE = (REPO / ".github/pull_request_template.md").read_text()


def filled_template() -> str:
    out = []
    for line in TEMPLATE.splitlines():
        out.append(line)
        if line.startswith("## "):
            out.append("Some real content.")
    return "\n".join(out)


def test_template_headings_match_expected_sections():
    """The checker's section list must stay in sync with the template."""
    problems = hc.check(filled_template())
    assert problems == []


def test_empty_template_fails_all_sections():
    problems = hc.check(TEMPLATE)
    assert len(problems) == len(hc.SECTIONS)
    assert all("empty" in p for p in problems)


def test_missing_section_reported():
    body = "\n".join(
        line for line in filled_template().splitlines() if "Out of scope" not in line
    )
    problems = hc.check(body)
    assert any("section 10" in p and "missing" in p for p in problems)


def test_html_comments_do_not_count_as_content():
    body = filled_template().replace(
        "Some real content.", "<!-- instructions only -->", 1
    )
    problems = hc.check(body)
    assert any("section 1" in p and "empty" in p for p in problems)


def test_wrong_title_reported():
    body = filled_template().replace("## 9. Next owner", "## 9. Next honor")
    problems = hc.check(body)
    assert any("section 9" in p and "expected title" in p for p in problems)


def test_empty_body_fails():
    problems = hc.check("")
    assert len(problems) == len(hc.SECTIONS)


# ---------------------- §86-C6 claim-channel rule (MEM-ORG-0004, 2026-07-18)

def test_role_branch_without_claim_fails():
    problems = hc.role_claim_problems("sde/TASK-002-widget", filled_template())
    assert len(problems) == 1
    assert "no machine-readable gate-role claim" in problems[0]


def test_role_branch_with_claim_passes():
    body = filled_template() + "\nrole: SAT\n"
    assert hc.role_claim_problems("sde/TASK-002-widget", body) == []


def test_claim_is_case_insensitive_and_mid_body():
    body = "## intro\nrole: pjm\nmore text"
    assert hc.role_claim_problems("pjm/plan-tweak", body) == []


def test_explicit_human_claim_accepted():
    body = filled_template() + "\nrole: HUMAN\n"
    assert hc.role_claim_problems("sat/review-notes", body) == []


def test_non_gate_role_word_is_not_a_claim():
    # SDE is not a claimable gate owner; a stray 'role: SDE' must not satisfy
    body = filled_template() + "\nrole: SDE\n"
    assert len(hc.role_claim_problems("sde/TASK-002-widget", body)) == 1


def test_claim_inside_html_comment_does_not_count():
    body = filled_template() + "\n<!--\nrole: SAT\n-->\n"
    assert len(hc.role_claim_problems("sde/TASK-002-widget", body)) == 1


def test_non_role_branches_unaffected():
    for ref in ("bootstrap/c6-claim-channel", "dispatch/TASK-001",
                "gate/pr-53", "owner/b7.1-sign-charter", "main", ""):
        assert hc.role_claim_problems(ref, "") == []


def test_all_role_prefixes_covered():
    assert len(hc.ROLE_BRANCH_PREFIXES) == 13  # ADR-B001 short codes
    for prefix in hc.ROLE_BRANCH_PREFIXES:
        assert hc.role_claim_problems(f"{prefix}/x", "") != []
