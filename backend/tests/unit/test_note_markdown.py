from app.lib.note_markdown import (
    html_to_text,
    note_source_markdown,
    source_filename_from_title,
)


def test_html_to_text_strips_empty_tiptap_markup():
    assert html_to_text("") == ""
    assert html_to_text("<p></p>") == ""
    assert html_to_text("<p><br></p>") == ""
    assert html_to_text("<p><br class='ProseMirror-trailingBreak'></p>") == ""


def test_html_to_text_keeps_paragraphs():
    assert html_to_text("<p>Hello</p><p>World</p>") == "Hello\n\nWorld"


def test_note_source_markdown_includes_title_and_user_html():
    markdown = note_source_markdown(
        "Meeting notes",
        {"kind": "user", "html": "<p>Bring the <strong>report</strong>.</p>"},
    )
    assert markdown == "# Meeting notes\n\nBring the report.\n"


def test_note_source_markdown_includes_title_and_chat_markdown():
    markdown = note_source_markdown(
        "Pinned answer",
        {"kind": "chat", "markdown": "## Findings\n\nSee [1](/citation/1)."},
    )
    assert markdown == "# Pinned answer\n\n## Findings\n\nSee [1](/citation/1).\n"


def test_note_source_markdown_empty_when_note_has_no_body():
    assert note_source_markdown("Title only", {"kind": "user", "html": "<p></p>"}) == ""
    assert note_source_markdown("Title only", {"kind": "chat", "markdown": "  "}) == ""


def test_source_filename_from_title_sanitizes_path_chars():
    assert source_filename_from_title("Q3 / Plan?") == "Q3 - Plan.md"
    assert source_filename_from_title("draft.") == "draft.md"
    assert source_filename_from_title("  ") == "New Note.md"
