from unittest.mock import MagicMock, patch

import pytest

from uvtask.commands import (
    CommandBuilder,
    CommandExecutorOrchestrator,
    CommandValidator,
    HelpCommandHandler,
    VerboseOutputHandler,
)


class TestCommandBuilder:
    def test_build_string_command(self) -> None:
        builder = CommandBuilder()
        commands = builder.build_commands("echo hello", ["world"])
        assert commands == ["echo hello world"]

    def test_build_string_command_no_args(self) -> None:
        builder = CommandBuilder()
        commands = builder.build_commands("echo hello", [])
        assert commands == ["echo hello"]

    def test_build_list_commands(self) -> None:
        builder = CommandBuilder()
        commands = builder.build_commands(["echo hello", "echo world"], ["test"])
        assert commands == ["echo hello test", "echo world test"]

    def test_build_list_commands_no_args(self) -> None:
        builder = CommandBuilder()
        commands = builder.build_commands(["echo hello", "echo world"], [])
        assert commands == ["echo hello", "echo world"]

    def test_build_with_command_reference(self) -> None:
        builder = CommandBuilder()
        scripts = {"lint": "ruff check .", "test": "pytest", "check": ["lint", "test"]}
        commands = builder.build_commands("check", [], scripts)
        assert "ruff check ." in commands
        assert "pytest" in commands

    def test_build_with_nested_references(self) -> None:
        builder = CommandBuilder()
        scripts = {"lint": "ruff check .", "format": "ruff format .", "static": ["lint", "format"], "all": ["static"]}
        commands = builder.build_commands("all", [], scripts)
        assert "ruff check ." in commands
        assert "ruff format ." in commands

    def test_build_circular_reference_detection(self) -> None:
        builder = CommandBuilder()
        scripts = {"a": "b", "b": "a"}
        with pytest.raises(ValueError, match="Circular reference"):
            builder.build_commands("a", [], scripts)

    def test_build_invalid_type(self) -> None:
        builder = CommandBuilder()
        with pytest.raises(ValueError, match="Invalid script format"):
            builder.build_commands(123, [])  # type: ignore[arg-type]


class TestCommandValidator:
    def test_validate_exists(self) -> None:
        validator = CommandValidator()
        scripts = {"test": "echo test"}
        validator.validate_exists("test", scripts)

    def test_validate_not_exists_raises(self) -> None:
        validator = CommandValidator()
        scripts = {"test": "echo test"}
        with pytest.raises(SystemExit) as exc_info:
            validator.validate_exists("unknown", scripts)
        assert exc_info.value.code == 1


class TestHelpCommandHandler:
    def test_handle_help_general(self) -> None:
        mock_parser = MagicMock()
        handler = HelpCommandHandler()
        with pytest.raises(SystemExit) as exc_info:
            handler.handle_help(None, {}, {}, mock_parser)
        assert exc_info.value.code == 0
        mock_parser.print_help.assert_called_once()

    def test_handle_help_specific_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        scripts = {"test": "echo test"}
        descriptions = {"test": "Test command"}
        mock_parser = MagicMock()
        handler = HelpCommandHandler()
        with pytest.raises(SystemExit) as exc_info:
            handler.handle_help("test", scripts, descriptions, mock_parser)
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Test command" in captured.out

    def test_handle_help_unknown_command(self) -> None:
        scripts = {"test": "echo test"}
        mock_parser = MagicMock()
        handler = HelpCommandHandler()
        with pytest.raises(SystemExit) as exc_info:
            handler.handle_help("unknown", scripts, {}, mock_parser)
        assert exc_info.value.code == 1


class TestVerboseOutputHandler:
    @patch("uvtask.commands.color_service")
    def test_show_execution_info(self, mock_color: MagicMock) -> None:
        mock_color.bold_green.side_effect = lambda x: x
        VerboseOutputHandler.show_execution_info("test", ["echo test"], ["pre"], ["post"], 1)
        assert mock_color.bold_green.called

    def test_show_execution_info_no_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        VerboseOutputHandler.show_execution_info("test", ["echo test"], [], [], 0)
        captured = capsys.readouterr()
        assert "Command: test" not in captured.err

    @patch("uvtask.commands.color_service")
    def test_show_hook_failure(self, mock_color: MagicMock) -> None:
        mock_color.bold_red.side_effect = lambda x: x
        VerboseOutputHandler.show_hook_failure("Pre-hook", 1, 1)
        assert mock_color.bold_red.called

    @patch("uvtask.commands.color_service")
    def test_show_command_failure(self, mock_color: MagicMock) -> None:
        mock_color.bold_red.side_effect = lambda x: x
        VerboseOutputHandler.show_command_failure(1, 1)
        assert mock_color.bold_red.called

    @patch("uvtask.commands.color_service")
    def test_show_final_exit_code(self, mock_color: MagicMock) -> None:
        mock_color.bold_green.side_effect = lambda x: x
        mock_color.bold_red.side_effect = lambda x: x
        VerboseOutputHandler.show_final_exit_code(0, 1)
        assert mock_color.bold_green.called


class TestCommandExecutorOrchestrator:
    def test_execute_success(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.return_value = 0
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], [], [], 0, 0)
        assert exc_info.value.code == 0
        mock_executor.execute.assert_called_once_with("echo test", 0, 0)

    def test_execute_with_pre_hooks(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.return_value = 0
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], ["echo pre"], [], 0, 0)
        assert exc_info.value.code == 0
        assert mock_executor.execute.call_count == 2

    def test_execute_pre_hook_failure(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.return_value = 1
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], ["echo pre"], [], 0, 0)
        assert exc_info.value.code == 1

    def test_execute_main_command_failure(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = [0, 1]
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], ["echo pre"], [], 0, 0)
        assert exc_info.value.code == 1

    def test_execute_with_post_hooks(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = [0, 0, 0]
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], ["echo pre"], ["echo post"], 0, 0)
        assert exc_info.value.code == 0
        assert mock_executor.execute.call_count == 3

    def test_execute_post_hook_failure(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = [0, 0, 1]
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], ["echo pre"], ["echo post"], 0, 0)
        assert exc_info.value.code == 1

    def test_execute_keyboard_interrupt(self) -> None:
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = KeyboardInterrupt()
        orchestrator = CommandExecutorOrchestrator(mock_executor)
        with pytest.raises(SystemExit) as exc_info:
            orchestrator.execute("test", ["echo test"], [], [], 0, 0)
        assert exc_info.value.code == 130
