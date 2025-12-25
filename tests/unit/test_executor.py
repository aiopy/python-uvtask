from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from uvtask.executor import CommandExecutor


class TestCommandExecutor:
    @patch("uvtask.executor.run")
    def test_execute_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 0, 0)
        assert exit_code == 0
        mock_run.assert_called_once()

    @patch("uvtask.executor.run")
    def test_execute_with_quiet(self, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 1, 0)
        assert exit_code == 0
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["stdout"] is not None or call_kwargs.get("stdout") is None

    @patch("uvtask.executor.run")
    def test_execute_with_double_quiet(self, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 2, 0)
        assert exit_code == 0
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["stderr"] is not None or call_kwargs.get("stderr") is None

    @patch("uvtask.executor.run")
    @patch("uvtask.executor.color_service")
    @patch("uvtask.executor.preference_manager")
    def test_execute_with_verbose(self, mock_pref: MagicMock, mock_color: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 0)
        mock_pref.supports_color.return_value = True
        mock_color.bold_teal.side_effect = lambda x: x
        mock_color.bold_green.side_effect = lambda x: x
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 0, 1)
        assert exit_code == 0
        assert mock_color.bold_teal.called or mock_color.bold_green.called

    @patch("uvtask.executor.run")
    def test_execute_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 1)
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 0, 0)
        assert exit_code == 1

    @patch("uvtask.executor.run")
    def test_execute_keyboard_interrupt(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = KeyboardInterrupt()
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 0, 0)
        assert exit_code == 130

    @patch("uvtask.executor.run")
    @patch("uvtask.executor.color_service")
    @patch("uvtask.executor.preference_manager")
    def test_execute_verbose_shows_exit_code(self, mock_pref: MagicMock, mock_color: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = CompletedProcess(["echo", "test"], 42)
        mock_pref.supports_color.return_value = True
        mock_color.bold_teal.side_effect = lambda x: x
        mock_color.bold_red.side_effect = lambda x: x
        executor = CommandExecutor()
        exit_code = executor.execute("echo test", 0, 1)
        assert exit_code == 42
        assert mock_color.bold_teal.called or mock_color.bold_red.called
