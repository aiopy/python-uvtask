import argparse
from unittest.mock import MagicMock, patch

from uvtask.parser import ArgumentParserBuilder, ArgvParser


class TestArgvParser:
    def test_parse_global_options_simple_command(self) -> None:
        parser = ArgvParser(["uvtask", "test"])
        scripts = {"test": "echo test"}
        command, args, quiet, verbose = parser.parse_global_options(scripts)
        assert command == "test"
        assert args == []
        assert quiet == 0
        assert verbose == 0

    def test_parse_global_options_with_args(self) -> None:
        parser = ArgvParser(["uvtask", "test", "arg1", "arg2"])
        scripts = {"test": "echo test"}
        command, args, quiet, verbose = parser.parse_global_options(scripts)
        assert command == "test"
        assert args == ["arg1", "arg2"]
        assert quiet == 0
        assert verbose == 0

    def test_parse_quiet_flag(self) -> None:
        parser = ArgvParser(["uvtask", "-q", "test"])
        scripts = {"test": "echo test"}
        _command, _args, quiet, verbose = parser.parse_global_options(scripts)
        assert quiet == 1
        assert verbose == 0

    def test_parse_multiple_quiet_flags(self) -> None:
        parser = ArgvParser(["uvtask", "-q", "-q", "test"])
        scripts = {"test": "echo test"}
        _command, _args, quiet, verbose = parser.parse_global_options(scripts)
        assert quiet == 2
        assert verbose == 0

    def test_parse_verbose_flag(self) -> None:
        parser = ArgvParser(["uvtask", "-v", "test"])
        scripts = {"test": "echo test"}
        _command, _args, quiet, verbose = parser.parse_global_options(scripts)
        assert quiet == 0
        assert verbose == 1

    def test_parse_multiple_verbose_flags(self) -> None:
        parser = ArgvParser(["uvtask", "-v", "-v", "test"])
        scripts = {"test": "echo test"}
        _command, _args, quiet, verbose = parser.parse_global_options(scripts)
        assert quiet == 0
        assert verbose == 2

    @patch("uvtask.parser.preference_manager")
    def test_parse_color_flag(self, mock_pref: MagicMock) -> None:
        parser = ArgvParser(["uvtask", "--color", "never", "test"])
        scripts = {"test": "echo test"}
        command, _args, _quiet, _verbose = parser.parse_global_options(scripts)
        assert command == "test"
        mock_pref.set_preference_from_string.assert_called_once_with("never")

    def test_parse_color_equals(self) -> None:
        parser = ArgvParser(["uvtask", "--color=always", "test"])
        scripts = {"test": "echo test"}
        with patch("uvtask.parser.preference_manager") as mock_pref:
            command, _args, _quiet, _verbose = parser.parse_global_options(scripts)
            assert command == "test"
            mock_pref.set_preference_from_string.assert_called_once_with("always")

    def test_parse_help_command(self) -> None:
        parser = ArgvParser(["uvtask", "help", "test"])
        scripts = {"test": "echo test"}
        command, args, _quiet, _verbose = parser.parse_global_options(scripts)
        assert command == "help"
        assert args == ["test"]

    def test_parse_no_command(self) -> None:
        parser = ArgvParser(["uvtask", "--version"])
        scripts = {}
        command, args, _quiet, _verbose = parser.parse_global_options(scripts)
        assert command is None
        assert args == []


class TestArgumentParserBuilder:
    def test_build_main_parser(self) -> None:
        mock_version_loader = MagicMock()
        mock_version_loader.get_version.return_value = "1.0.0"
        builder = ArgumentParserBuilder(mock_version_loader)
        parser = builder.build_main_parser()
        assert parser.prog == "uvtask"
        assert parser.description == "An extremely fast Python task runner."

    def test_add_subparsers(self) -> None:
        mock_version_loader = MagicMock()
        mock_version_loader.get_version.return_value = "1.0.0"
        builder = ArgumentParserBuilder(mock_version_loader)
        parser = builder.build_main_parser()
        scripts = {"test": "echo test", "build": "echo build"}
        descriptions = {"test": "Test command", "build": "Build command"}
        builder.add_subparsers(parser, scripts, descriptions)
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert subparsers_action is not None
        assert "test" in subparsers_action.choices
        assert "build" in subparsers_action.choices
        assert "help" in subparsers_action.choices

    def test_add_subparsers_skips_hooks(self) -> None:
        mock_version_loader = MagicMock()
        mock_version_loader.get_version.return_value = "1.0.0"
        builder = ArgumentParserBuilder(mock_version_loader)
        parser = builder.build_main_parser()
        scripts = {"test": "echo test", "pre-test": "echo pre", "post-test": "echo post"}
        descriptions = {}
        builder.add_subparsers(parser, scripts, descriptions)
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        assert subparsers_action is not None
        choices = subparsers_action.choices
        assert "test" in choices
        assert "pre-test" not in choices
        assert "post-test" not in choices
