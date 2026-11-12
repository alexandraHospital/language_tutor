"""Pytest configuration for the tutor test suite.

tutor.py imports heavy application dependencies (ollama, mistralai, openai,
piper, dotenv) at module level. The tests only exercise pure helpers, so
those imports are stubbed here, before any test module imports tutor: no
test environment needs the real packages installed.
"""

import sys
import types
from pathlib import Path

import pytest

# Make the repository root importable: tutor.py lives at the root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Attributes imported by tutor.py for each stubbed module.
_STUB_ATTRIBUTES = {
    "ollama": {"chat"},
    "mistralai": set(),
    "mistralai.client": {"Mistral"},
    "openai": {"OpenAI"},
    "piper": {"PiperVoice"},
    "dotenv": {"load_dotenv"},
}


def _install_import_stubs():
    for name, attributes in _STUB_ATTRIBUTES.items():
        module = types.ModuleType(name)

        for attribute in attributes:
            setattr(module, attribute, None)

        sys.modules[name] = module


_install_import_stubs()


def _build_log_header(kind="Briefing", language="English"):
    """Build the header written by ConversationLogger at session start."""
    return (
        f"{language} Tutor Session - {kind}\n"
        + "=" * 60
        + "\nStarted: 2026-11-10 14:12:53\n\n"
    )


@pytest.fixture
def log_header():
    """Return a builder for the standard log file header."""
    return _build_log_header


@pytest.fixture
def make_log_file(tmp_path, log_header):
    """Return a factory writing a log file with the standard header."""

    def _make(name, kind="Briefing", language="English", content=None):
        text = log_header(kind, language)
        if content is not None:
            text += content

        path = tmp_path / name
        path.write_text(text, encoding="utf-8")

        return path

    return _make
