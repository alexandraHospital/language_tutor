"""Tests for the follow-up feature of tutor.py.

Run from the repository root:

    pytest -q

The heavy application dependencies are stubbed in conftest.py, so these
tests only need the standard library and pytest.
"""

import sys
from pathlib import Path

import pytest

import tutor

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
# Session logs are stored per language: logs/<language_code>/.
LANGUAGE_LOGS_DIR = LOGS_DIR / "en"


# --- split_feedback_and_briefing ---


def test_split_feedback_and_briefing_delimiter_on_own_line_returns_both_parts():
    response = (
        "# Session Feedback\n\nLearner feedback.\n\n"
        f"{tutor.BRIEFING_DELIMITER}\n\n# Briefing content."
    )

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == "# Session Feedback\n\nLearner feedback."
    assert briefing == "# Briefing content."


def test_split_feedback_and_briefing_no_delimiter_returns_feedback_only():
    response = "# Session Feedback\n\nLearner feedback only."

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == response.strip()
    assert briefing is None


def test_split_feedback_and_briefing_delimiter_with_spaces_is_recognized():
    response = "Feedback.\n<<< TUTOR_BRIEFING >>>\nBriefing."

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == "Feedback."
    assert briefing == "Briefing."


def test_split_feedback_and_briefing_second_delimiter_kept_in_briefing():
    delimiter = tutor.BRIEFING_DELIMITER
    response = f"Feedback.\n{delimiter}\nFirst part.\n{delimiter}\nSecond part."

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == "Feedback."
    assert briefing == f"First part.\n{delimiter}\nSecond part."


def test_split_feedback_and_briefing_empty_briefing_returns_none():
    response = f"Feedback.\n{tutor.BRIEFING_DELIMITER}\n"

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == "Feedback."
    assert briefing is None


def test_split_feedback_and_briefing_delimiter_on_first_line_returns_empty_feedback():
    response = f"{tutor.BRIEFING_DELIMITER}\nBriefing."

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == ""
    assert briefing == "Briefing."


def test_split_feedback_and_briefing_delimiter_inside_sentence_is_ignored():
    response = "Feedback mentioning <<<TUTOR_BRIEFING>>> inline only."

    feedback, briefing = tutor.split_feedback_and_briefing(response)

    assert feedback == response.strip()
    assert briefing is None


# --- extract_briefing ---


def test_extract_briefing_header_only_file_returns_empty_string(log_header):
    assert tutor.extract_briefing(log_header()) == ""


def test_extract_briefing_content_after_header_returns_content(log_header):
    text = log_header() + "# Briefing content."

    assert tutor.extract_briefing(text) == "# Briefing content."


# --- ConversationLogger ---


def test_conversation_logger_session_start_creates_three_log_files(tmp_path):
    logger = tutor.ConversationLogger(tmp_path, "English")

    assert logger.conversation_path.exists()
    assert logger.feedback_path.exists()
    assert logger.briefing_path.exists()
    assert logger.briefing_path.name.endswith("_briefing.md")

    header = logger.briefing_path.read_text(encoding="utf-8")
    assert "English Tutor Session - Briefing" in header


def test_write_briefing_second_call_replaces_first_briefing(tmp_path):
    logger = tutor.ConversationLogger(tmp_path, "English")

    logger.write_briefing("First briefing.")
    logger.write_briefing("Second briefing.")

    text = logger.briefing_path.read_text(encoding="utf-8")
    assert "First briefing." not in text
    assert text.count("Second briefing.") == 1
    # The language header is kept after a rewrite.
    assert "English Tutor Session - Briefing" in text


def test_write_feedback_second_call_appends_after_first(tmp_path):
    logger = tutor.ConversationLogger(tmp_path, "English")

    logger.write_feedback("First feedback.")
    logger.write_feedback("Second feedback.")

    text = logger.feedback_path.read_text(encoding="utf-8")
    assert "First feedback." in text
    assert "Second feedback." in text


# --- find_latest_briefing_file ---


def test_conversation_logger_language_subdirectory_lookup_finds_written_briefing(
    tmp_path,
):
    # main() stores session logs in <logs_dir>/<language_code>/.
    language_logs_dir = tmp_path / "en"
    logger = tutor.ConversationLogger(language_logs_dir, "English")

    logger.write_briefing("Briefing content.")

    found = tutor.find_latest_briefing_file(language_logs_dir, "English")

    assert found == logger.briefing_path


def test_find_latest_briefing_file_unusable_files_skipped_returns_latest_usable(
    make_log_file, tmp_path
):
    # Most recent file was started but never got a briefing: skipped.
    make_log_file("session_20261111_090000_briefing.md")
    # Wrong language: skipped.
    make_log_file(
        "session_20261110_141300_briefing.md",
        language="French",
        content="Bonjour.",
    )
    # Feedback files are never matched by the briefing lookup.
    make_log_file(
        "session_20261110_141400_feedback.md",
        kind="Feedback",
        content="Hello.",
    )
    # Old log format (conversation log without suffix): not matched.
    make_log_file("session_20261110_142000.md", kind="", language="")
    expected = make_log_file("session_20261110_141200_briefing.md", content="Hello.")

    found = tutor.find_latest_briefing_file(tmp_path, "English")

    assert found == expected


def test_find_latest_briefing_file_no_usable_file_returns_none(make_log_file, tmp_path):
    make_log_file(
        "session_20261110_141253_briefing.md",
        language="French",
        content="Bonjour.",
    )

    assert tutor.find_latest_briefing_file(tmp_path, "English") is None


def test_find_latest_briefing_file_missing_directory_returns_none(tmp_path):
    assert tutor.find_latest_briefing_file(tmp_path / "nope", "English") is None


# --- build_followup_context ---


def test_build_followup_context_with_notes_returns_instructions_and_notes():
    context = tutor.build_followup_context("Retell the int32 bug story.")

    assert "[Previous session context]" in context
    assert "Retell the int32 bug story." in context
    assert "priority exercises" in context
    assert "<previous session notes>" in context


# --- parse_args ---


def test_parse_args_followup_flags_set_flags(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["tutor.py", "--followup", "--briefing_file", "x.md"]
    )

    args = tutor.parse_args()

    assert args.followup is True
    assert args.briefing_file == "x.md"


def test_parse_args_no_option_followup_off_by_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tutor.py"])

    args = tutor.parse_args()

    assert args.followup is False
    assert args.briefing_file is None


# --- Real logs ---


def test_find_latest_briefing_file_real_logs_returns_usable_briefing():
    if not LANGUAGE_LOGS_DIR.is_dir():
        pytest.skip("no logs directory")

    found = tutor.find_latest_briefing_file(LANGUAGE_LOGS_DIR, "English")

    if found is None:
        pytest.skip("no English briefing in logs yet")

    assert found.name.endswith("_briefing.md")
    assert tutor.extract_briefing(found.read_text(encoding="utf-8"))
