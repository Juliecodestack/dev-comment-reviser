# tests/test_llm.py — reply parsing. No network, no API key, no cost.
import pytest

import llm

HAPPY = """## Revised Text
This is the revised comment, still in the author's voice.

## Paragraph Explanations
**Paragraph 1**
- Fixed subject-verb agreement.
"""


def test_happy_path_splits_both_sections():
    revised, explanations = llm.split_sections(HAPPY)
    assert revised == "This is the revised comment, still in the author's voice."
    assert "Fixed subject-verb agreement" in explanations


def test_heading_quoted_inside_the_comment_is_not_a_boundary():
    """The model is allowed to echo the author's markdown, so a quoted heading
    must not cut the revision in half."""
    reply = (
        "## Revised Text\n"
        "Small note: the tool I use prints\n"
        "\n"
        "## Paragraph Explanations\n"
        "\n"
        "before every answer, which is confusing. Are you seeing the same thing?\n"
        "\n"
        "## Paragraph Explanations\n"
        "**Paragraph 1**\n"
        "- No changes needed.\n"
    )
    revised, explanations = llm.split_sections(reply)
    assert "before every answer" in revised
    assert "Small note" in revised
    assert "No changes needed" in explanations


def test_bold_headings_are_accepted():
    reply = "**Revised Text**\nFixed.\n\n**Paragraph Explanations**\n- one fix\n"
    revised, explanations = llm.split_sections(reply)
    assert revised == "Fixed."
    assert "one fix" in explanations


def test_lowercase_headings_are_accepted():
    reply = "## revised text\nFixed.\n\n## paragraph explanations\n- one fix\n"
    revised, _ = llm.split_sections(reply)
    assert revised == "Fixed."


def test_third_level_headings_are_accepted():
    reply = "### Revised Text\nFixed.\n\n### Paragraph Explanations\n- one fix\n"
    revised, _ = llm.split_sections(reply)
    assert revised == "Fixed."


def test_heading_with_trailing_colon_is_accepted():
    reply = "## Revised Text:\nFixed.\n\n## Paragraph Explanations:\n- one fix\n"
    revised, _ = llm.split_sections(reply)
    assert revised == "Fixed."


def test_heading_with_content_on_the_same_line():
    reply = "## Revised Text Fixed already.\n\n## Paragraph Explanations - one fix\n"
    revised, explanations = llm.split_sections(reply)
    assert revised == "Fixed already."
    assert explanations == "- one fix"


def test_crlf_line_endings():
    reply = "## Revised Text\r\nFixed.\r\n\r\n## Paragraph Explanations\r\n- one fix\r\n"
    revised, _ = llm.split_sections(reply)
    assert revised == "Fixed."


def test_empty_revised_section_is_rejected():
    reply = "## Revised Text\n\n## Paragraph Explanations\n\n"
    with pytest.raises(llm.LLMError):
        llm.split_sections(reply)


def test_missing_sections_are_rejected():
    with pytest.raises(llm.LLMError):
        llm.split_sections("Sure! Here is a cleaner version of your comment.")


def test_explanations_before_revised_is_rejected():
    reply = "## Paragraph Explanations\n- x\n\n## Revised Text\nFixed.\n"
    with pytest.raises(llm.LLMError):
        llm.split_sections(reply)
