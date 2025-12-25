from __future__ import annotations

from sys import argv

from uvtask.colors import preference_manager
from uvtask.config import VersionLoader
from uvtask.formatters import CustomArgumentParser


class ArgvParser:
    def __init__(self, argv_list: list[str] | None = None):
        self._argv = argv_list if argv_list is not None else argv

    def parse_global_options(self, scripts: dict[str, str | list[str]]) -> tuple[str | None, list[str], int, int]:
        script_args_list = []
        command_name = None
        skip_next = False
        quiet_count = 0
        verbose_count = 0

        for i, arg in enumerate(self._argv[1:], 1):
            if skip_next:
                skip_next = False
                # Process the color value (current arg is the value after --color)
                preference_manager.set_preference_from_string(arg)
                continue
            if arg == "--color":
                skip_next = True
                continue
            if arg.startswith("--color="):
                color_val = arg.split("=", 1)[1]
                preference_manager.set_preference_from_string(color_val)
                continue
            if arg in ["-q", "--quiet"]:
                quiet_count += 1
                continue
            if arg in ["-v", "--verbose"]:
                verbose_count += 1
                continue
            if arg in ["-V", "--version", "-h", "--help"]:
                continue
            if arg in ["--no-hooks", "--ignore-scripts"]:
                continue
            if arg in scripts or arg == "help":
                command_name = arg
                script_args_list = self._argv[i + 1 :]
                break

        return command_name, script_args_list, quiet_count, verbose_count


class ArgumentParserBuilder:
    def __init__(self, version_loader: VersionLoader):
        self._version_loader = version_loader

    def build_main_parser(self) -> CustomArgumentParser:
        parser = CustomArgumentParser(
            prog="uvtask",
            description="An extremely fast Python task runner.",
            epilog="Use `uvtask help` for more details.",
        )

        parser.add_argument(
            "-q",
            "--quiet",
            action="count",
            default=0,
            help="Use quiet output",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="Use verbose output",
        )
        parser.add_argument(
            "--no-hooks",
            "--ignore-scripts",
            dest="no_hooks",
            action="store_true",
            help="Skip running pre and post hooks/scripts",
        )
        parser.add_argument(
            "--color",
            choices=["auto", "always", "never"],
            default="auto",
            metavar="COLOR_CHOICE",
            help="Control the use of color in output [possible values: auto, always, never]",
        )
        parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {self._version_loader.get_version()}",
        )

        return parser

    def add_subparsers(self, parser: CustomArgumentParser, scripts: dict[str, str | list[str]], script_descriptions: dict[str, str]) -> None:
        subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

        for script_name, script_command in scripts.items():
            if self._is_hook(script_name, scripts):
                continue

            description = script_descriptions.get(script_name, f"Run {script_name}")
            help_text = script_descriptions.get(script_name, f"Run {script_name}")
            subparsers.add_parser(script_name, help=help_text, description=description)

        help_parser = subparsers.add_parser("help", help="Display documentation for a command", description="Display documentation for a command")
        help_parser.add_argument("command_name", nargs="?", help="The command to show help for")

    @staticmethod
    def _is_hook(script_name: str, all_scripts: dict[str, str | list[str]]) -> bool:
        for cmd_name in all_scripts.keys():
            if cmd_name == script_name:
                continue
            if script_name in (f"pre-{cmd_name}", f"post-{cmd_name}"):
                return True
            if script_name in (f"pre{cmd_name}", f"post{cmd_name}"):
                return True
        return False
