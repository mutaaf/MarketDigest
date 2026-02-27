"""Test message formatting and splitting."""

from src.digest.formatter import MAX_MESSAGE_LENGTH, bold, esc, split_message


def test_short_message_no_split():
    """Messages under 4096 chars should not be split."""
    msg = "Hello world"
    result = split_message(msg)
    assert result == [msg]


def test_long_message_splits():
    """Messages over 4096 chars should be split into multiple chunks."""
    # Create a message that's definitely over the limit
    sections = []
    for i in range(20):
        sections.append(f"\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n<b>Section {i}</b>\n{'x' * 300}")
    msg = "\n".join(sections)
    assert len(msg) > MAX_MESSAGE_LENGTH

    result = split_message(msg)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= MAX_MESSAGE_LENGTH


def test_bold_escapes_html():
    assert bold("A&B") == "<b>A&amp;B</b>"


def test_esc_html_entities():
    assert esc("<script>") == "&lt;script&gt;"
    assert esc("a&b") == "a&amp;b"
