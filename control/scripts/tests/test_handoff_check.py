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
