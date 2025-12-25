import argparse
from unittest.mock import MagicMock, patch

import pytest

from uvtask.formatters import (
    AnsiStripper,
    CommandMatcher,
    CustomArgumentParser,
    CustomHelpFormatter,
    HelpTextProcessor,
    OptionSorter,
)


class TestCommandMatcher:
    def test_find_similar_exact_match(self) -> None:
        matcher = CommandMatcher()
        result = matcher.find_similar("test", ["test", "build", "lint"])
        assert result == "test"

    def test_find_similar_prefix(self) -> None:
        matcher = CommandMatcher()
        result = matcher.find_similar("tes", ["test", "build"])
        assert result == "test"

    def test_find_similar_levenshtein(self) -> None:
        matcher = CommandMatcher()
        result = matcher.find_similar("buil", ["build", "test"])
        assert result == "build"

    def test_find_similar_no_match(self) -> None:
        matcher = CommandMatcher()
        result = matcher.find_similar("xyz", ["test", "build"])
        assert result is None

    def test_find_similar_empty_list(self) -> None:
        matcher = CommandMatcher()
        result = matcher.find_similar("test", [])
        assert result is None


class TestAnsiStripper:
    def test_strip_ansi_codes(self) -> None:
        text = "\x1b[1m\x1b[31mHello\x1b[0m"
        result = AnsiStripper.strip(text)
        assert result == "Hello"

    def test_strip_no_codes(self) -> None:
        text = "Hello"
        result = AnsiStripper.strip(text)
        assert result == "Hello"


class TestOptionSorter:
    def test_sort_options(self) -> None:
        lines = [
            "  -h, --help",
            "  -V, --version",
            "  -q, --quiet",
            "  -v, --verbose",
        ]
        result = OptionSorter.sort(lines)
        assert "-q" in result[0] or "--quiet" in result[0]
        assert "-h" in result[-1] or "--help" in result[-1]


class TestHelpTextProcessor:
    def test_process_help_text(self) -> None:
        processor = HelpTextProcessor(AnsiStripper())
        help_text = "Description\n\nCommands:\n  test\n\nGlobal options:\n  -h, --help"
        result = processor.process_help_text(help_text)
        assert "Usage:" in result or "Commands:" in result

    def test_add_usage_line(self) -> None:
        processor = HelpTextProcessor(AnsiStripper())
        result = []
        processor._add_usage_line(result)
        assert len(result) == 2
        assert "Usage:" in result[0]


class TestCustomHelpFormatter:
    def test_format_action_invocation_option(self) -> None:
        formatter = CustomHelpFormatter(prog="test")
        action = argparse.Action("--test", dest="test", help="Test option")
        action.option_strings = ["--test"]
        result = formatter._format_action_invocation(action)
        assert "--test" in result

    def test_format_action_invocation_count_action(self) -> None:
        formatter = CustomHelpFormatter(prog="test")
        action = argparse._CountAction("--quiet", dest="quiet", help="Quiet")
        action.option_strings = ["-q", "--quiet"]
        result = formatter._format_action_invocation(action)
        assert "..." in result

    def test_get_metavar_str(self) -> None:
        formatter = CustomHelpFormatter(prog="test")
        action = argparse.Action("--color", dest="color", help="Color")
        action.option_strings = ["--color"]
        action.choices = ["auto", "always", "never"]
        result = formatter._get_metavar_str(action)
        assert result == "COLOR_CHOICE"


class TestCustomArgumentParser:
    def test_init(self) -> None:
        parser = CustomArgumentParser(prog="test")
        assert parser.prog == "test"
        assert isinstance(parser._command_matcher, CommandMatcher)

    @patch("uvtask.formatters.preference_manager")
    def test_error_invalid_choice(self, mock_pref: MagicMock) -> None:
        parser = CustomArgumentParser(prog="test")
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("test")
        with pytest.raises(SystemExit) as exc_info:
            parser.error("argument COMMAND: invalid choice: 'unknown' (choose from 'test')")
        assert exc_info.value.code == 1
