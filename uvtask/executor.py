from __future__ import annotations

from subprocess import DEVNULL, run  # nosec B404
from sys import stderr

from uvtask.colors import color_service, preference_manager


class CommandExecutor:
    def _print_verbose_command(self, command: str) -> None:
        cmd_text = color_service.bold_teal(f"Running: {command}") if preference_manager.supports_color() else f"Running: {command}"
        print(cmd_text, file=stderr)

    def _print_verbose_exit_code(self, exit_code: int) -> None:
        exit_text = color_service.bold_green(f"Exit code: {exit_code}") if exit_code == 0 else color_service.bold_red(f"Exit code: {exit_code}")
        print(exit_text, file=stderr)

    def _execute_quiet(self, command: str, quiet_count: int, verbose_count: int) -> int:
        result = run(
            command,
            shell=True,
            check=False,
            stdout=DEVNULL if quiet_count >= 1 else None,
            stderr=DEVNULL if quiet_count >= 2 else None,
        )  # nosec B602
        if verbose_count > 0:
            self._print_verbose_exit_code(result.returncode)
        return result.returncode

    def _execute_normal(self, command: str, verbose_count: int) -> int:
        result = run(command, check=False, shell=True)  # nosec B602
        if verbose_count > 0:
            self._print_verbose_exit_code(result.returncode)
        return result.returncode

    def execute(
        self,
        command: str,
        quiet_count: int = 0,
        verbose_count: int = 0,
    ) -> int:
        try:
            if verbose_count > 0:
                self._print_verbose_command(command)

            if quiet_count > 0:
                return self._execute_quiet(command, quiet_count, verbose_count)
            return self._execute_normal(command, verbose_count)
        except KeyboardInterrupt:
            if verbose_count > 0:
                print(color_service.bold_red("Interrupted by user"), file=stderr)
            return 130


command_executor = CommandExecutor()
