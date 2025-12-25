import subprocess
from subprocess import run
from sys import stderr

from uvtask.colors import color_service, preference_manager


class CommandExecutor:
    def execute(
        self,
        command: str,
        quiet_count: int = 0,
        verbose_count: int = 0,
    ) -> int:
        try:
            if verbose_count > 0:
                cmd_text = color_service.bold_teal(f"Running: {command}") if preference_manager.supports_color() else f"Running: {command}"
                print(cmd_text, file=stderr)

            if quiet_count > 0:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=False,
                    stdout=subprocess.DEVNULL if quiet_count >= 1 else None,
                    stderr=subprocess.DEVNULL if quiet_count >= 2 else None,
                )
                if verbose_count > 0:
                    exit_text = (
                        color_service.bold_green(f"Exit code: {result.returncode}")
                        if result.returncode == 0
                        else color_service.bold_red(f"Exit code: {result.returncode}")
                    )
                    print(exit_text, file=stderr)
                return result.returncode
            else:
                result = run(command, check=False, shell=True)
                if verbose_count > 0:
                    exit_text = (
                        color_service.bold_green(f"Exit code: {result.returncode}")
                        if result.returncode == 0
                        else color_service.bold_red(f"Exit code: {result.returncode}")
                    )
                    print(exit_text, file=stderr)
                return result.returncode
        except KeyboardInterrupt:
            if verbose_count > 0:
                print(color_service.bold_red("Interrupted by user"), file=stderr)
            return 130


command_executor = CommandExecutor()
