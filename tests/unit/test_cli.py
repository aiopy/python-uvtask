"""Unit tests for uvtask CLI."""

import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from uvtask.cli import main


class TestCLI:
    """Test cases for CLI functionality."""

    def test_missing_pyproject_toml(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error when pyproject.toml is missing."""
        # Change to temp directory without pyproject.toml
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(temp_dir)
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: pyproject.toml not found in current directory!" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_help_output(self, pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test help output displays available commands."""
        original_cwd = Path.cwd()
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "-h"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "Usage: uvtask [COMMAND]" in captured.out
            assert "test" in captured.out
            assert "build" in captured.out
            assert "lint" in captured.out
            assert "-h,--help" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_help_variants(self, pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test different help flag variants."""
        original_cwd = Path.cwd()
        try:
            os.chdir(pyproject_toml.parent)

            for help_flag in ["-h", "-help", "--help"]:
                with patch("uvtask.cli.argv", ["uvtask", help_flag]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                captured = capsys.readouterr()
                assert "Usage: uvtask [COMMAND]" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_no_args_shows_help(self, pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that no arguments defaults to help."""
        original_cwd = Path.cwd()
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "Usage: uvtask [COMMAND]" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_unknown_command(self, pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error for unknown command."""
        original_cwd = Path.cwd()
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "unknown-command"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: Unknown command 'unknown-command'!" in captured.out
            assert "Run 'uvtask --help' to see available commands." in captured.out
        finally:
            os.chdir(original_cwd)

    @patch("uvtask.cli.run")
    def test_command_execution(self, mock_run: MagicMock, pyproject_toml: Path) -> None:
        """Test that commands are executed correctly."""
        original_cwd = Path.cwd()
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "test"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            mock_run.assert_called_once_with("echo test", check=False, shell=True)
        finally:
            os.chdir(original_cwd)

    @patch("uvtask.cli.run")
    def test_command_with_args(self, mock_run: MagicMock, pyproject_toml: Path) -> None:
        """Test command execution with additional arguments."""
        original_cwd = Path.cwd()
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "test", "--verbose", "arg1", "arg2"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            mock_run.assert_called_once_with("echo test --verbose arg1 arg2", check=False, shell=True)
        finally:
            os.chdir(original_cwd)

    def test_command_with_dollar_at_placeholder(self, temp_dir: Path) -> None:
        """Test command with $@ placeholder for arguments."""
        original_cwd = Path.cwd()
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_content = """[tool.run-script]
format = "uv run ruff format $@"
"""
        pyproject_path.write_text(pyproject_content)
        mock_run = MagicMock(return_value=CompletedProcess(["uv", "run"], 0))
        try:
            os.chdir(temp_dir)
            with patch("uvtask.cli.run", mock_run):
                with patch("uvtask.cli.argv", ["uvtask", "format", "src", "tests"]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                # Note: $@ is not replaced, arguments are appended after the script
                mock_run.assert_called_once_with("uv run ruff format $@ src tests", check=False, shell=True)
        finally:
            os.chdir(original_cwd)

    @patch("uvtask.cli.run")
    def test_command_exit_code_propagation(self, mock_run: MagicMock, pyproject_toml: Path) -> None:
        """Test that command exit codes are propagated."""
        original_cwd = Path.cwd()
        mock_run.return_value = CompletedProcess(["echo", "test"], 42)
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "test"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 42
        finally:
            os.chdir(original_cwd)

    @patch("uvtask.cli.run")
    def test_keyboard_interrupt(self, mock_run: MagicMock, pyproject_toml: Path) -> None:
        """Test KeyboardInterrupt handling."""
        original_cwd = Path.cwd()
        mock_run.side_effect = KeyboardInterrupt()
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "test"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 130
        finally:
            os.chdir(original_cwd)

    def test_multi_word_command(self, pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test commands with multi-word names."""
        original_cwd = Path.cwd()
        try:
            os.chdir(pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "-h"]):
                with pytest.raises(SystemExit):
                    main()
            captured = capsys.readouterr()
            assert "multi-word" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_empty_run_script_section(self, empty_pyproject_toml: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test behavior when run-script section is missing."""
        original_cwd = Path.cwd()
        try:
            os.chdir(empty_pyproject_toml.parent)
            with patch("uvtask.cli.argv", ["uvtask", "-h"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            captured = capsys.readouterr()
            # Should show help with no commands listed
            assert "Usage: uvtask [COMMAND]" in captured.out
        finally:
            os.chdir(original_cwd)
