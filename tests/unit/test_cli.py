from pathlib import Path
from unittest.mock import MagicMock

import pytest

from uvtask.cli import CliApplication


class TestCliApplication:
    def test_run_missing_pyproject(self, temp_dir: Path) -> None:
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(temp_dir)
            mock_script_loader = MagicMock()
            mock_version_loader = MagicMock()
            mock_parser_builder = MagicMock()
            mock_argv_parser = MagicMock()
            mock_validator = MagicMock()
            mock_builder = MagicMock()
            mock_help_handler = MagicMock()
            mock_orchestrator = MagicMock()

            app = CliApplication(
                mock_script_loader,
                mock_version_loader,
                mock_parser_builder,
                mock_argv_parser,
                mock_validator,
                mock_builder,
                mock_help_handler,
                mock_orchestrator,
            )

            with pytest.raises(SystemExit) as exc_info:
                app.run()
            assert exc_info.value.code == 1
        finally:
            os.chdir(original_cwd)

    def test_run_validates_reserved_commands(self, pyproject_toml: Path) -> None:
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(pyproject_toml.parent)
            mock_script_loader = MagicMock()
            mock_script_loader.load_scripts_with_descriptions.return_value = ({"help": "echo help"}, {})
            mock_version_loader = MagicMock()
            mock_parser_builder = MagicMock()
            mock_argv_parser = MagicMock()
            mock_validator = MagicMock()
            mock_builder = MagicMock()
            mock_help_handler = MagicMock()
            mock_orchestrator = MagicMock()

            app = CliApplication(
                mock_script_loader,
                mock_version_loader,
                mock_parser_builder,
                mock_argv_parser,
                mock_validator,
                mock_builder,
                mock_help_handler,
                mock_orchestrator,
            )

            with pytest.raises(SystemExit) as exc_info:
                app.run()
            assert exc_info.value.code == 1
        finally:
            os.chdir(original_cwd)

    def test_run_executes_command(self, pyproject_toml: Path) -> None:
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(pyproject_toml.parent)
            mock_script_loader = MagicMock()
            mock_script_loader.load_scripts_with_descriptions.return_value = (
                {"test": "echo test"},
                {"test": "Test command"},
            )
            mock_version_loader = MagicMock()
            mock_parser_builder = MagicMock()
            mock_parser = MagicMock()
            mock_parser_builder.build_main_parser.return_value = mock_parser
            mock_argv_parser = MagicMock()
            mock_argv_parser.parse_global_options.return_value = ("test", [], 0, 0)
            mock_validator = MagicMock()
            mock_builder = MagicMock()
            mock_builder.build_commands.return_value = ["echo test"]
            mock_help_handler = MagicMock()
            mock_orchestrator = MagicMock()
            mock_orchestrator.execute.side_effect = SystemExit(0)

            app = CliApplication(
                mock_script_loader,
                mock_version_loader,
                mock_parser_builder,
                mock_argv_parser,
                mock_validator,
                mock_builder,
                mock_help_handler,
                mock_orchestrator,
            )

            with pytest.raises(SystemExit) as exc_info:
                app.run()
            assert exc_info.value.code == 0
            mock_orchestrator.execute.assert_called_once()
        finally:
            os.chdir(original_cwd)

    def test_run_handles_help_command(self, pyproject_toml: Path) -> None:
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(pyproject_toml.parent)
            mock_script_loader = MagicMock()
            mock_script_loader.load_scripts_with_descriptions.return_value = ({"test": "echo test"}, {})
            mock_version_loader = MagicMock()
            mock_parser_builder = MagicMock()
            mock_parser = MagicMock()
            mock_parser_builder.build_main_parser.return_value = mock_parser
            mock_argv_parser = MagicMock()
            mock_argv_parser.parse_global_options.return_value = ("help", [], 0, 0)
            mock_validator = MagicMock()
            mock_builder = MagicMock()
            mock_help_handler = MagicMock()
            mock_help_handler.handle_help.side_effect = SystemExit(0)
            mock_orchestrator = MagicMock()

            app = CliApplication(
                mock_script_loader,
                mock_version_loader,
                mock_parser_builder,
                mock_argv_parser,
                mock_validator,
                mock_builder,
                mock_help_handler,
                mock_orchestrator,
            )

            with pytest.raises(SystemExit) as exc_info:
                app.run()
            assert exc_info.value.code == 0
            mock_help_handler.handle_help.assert_called_once()
        finally:
            os.chdir(original_cwd)
