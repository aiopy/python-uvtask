from pathlib import Path
from sys import exit, stderr

from uvtask.colors import color_service
from uvtask.commands import (
    CommandBuilder,
    CommandExecutorOrchestrator,
    CommandValidator,
    HelpCommandHandler,
)
from uvtask.config import ScriptLoader, VersionLoader, script_loader, version_loader
from uvtask.executor import command_executor
from uvtask.formatters import CustomArgumentParser
from uvtask.hooks import argv_hook_flag_parser, hook_discoverer
from uvtask.parser import ArgumentParserBuilder, ArgvParser


class CliApplication:
    def __init__(
        self,
        script_loader: ScriptLoader,
        version_loader: VersionLoader,
        parser_builder: ArgumentParserBuilder,
        argv_parser: ArgvParser,
        command_validator: CommandValidator,
        command_builder: CommandBuilder,
        help_handler: HelpCommandHandler,
        executor_orchestrator: CommandExecutorOrchestrator,
    ):
        self._script_loader = script_loader
        self._version_loader = version_loader
        self._parser_builder = parser_builder
        self._argv_parser = argv_parser
        self._command_validator = command_validator
        self._command_builder = command_builder
        self._help_handler = help_handler
        self._executor_orchestrator = executor_orchestrator

    def run(self) -> None:
        self._validate_pyproject_exists()
        scripts, script_descriptions = self._script_loader.load_scripts_with_descriptions()
        self._validate_reserved_commands(scripts)

        parser = self._parser_builder.build_main_parser()
        self._parser_builder.add_subparsers(parser, scripts, script_descriptions)

        command_name, script_args, quiet_count, verbose_count = self._argv_parser.parse_global_options(scripts)

        if not command_name:
            command_name = self._get_command_from_argparse(parser)

        if command_name == "help":
            self._help_handler.handle_help(script_args[0] if script_args else None, scripts, script_descriptions, parser)

        self._command_validator.validate_exists(command_name, scripts)

        script = scripts.get(command_name)
        if script is None:
            # This should never happen after validate_exists, but type checker needs this
            self._command_validator.validate_exists(command_name, scripts)
            return

        no_hooks = argv_hook_flag_parser.parse_no_hooks()
        pre_hooks, post_hooks = hook_discoverer.discover(command_name, scripts) if not no_hooks else ([], [])

        main_commands = self._command_builder.build_commands(script, script_args, scripts)

        self._executor_orchestrator.execute(command_name, main_commands, pre_hooks, post_hooks, quiet_count, verbose_count)

    @staticmethod
    def _validate_pyproject_exists() -> None:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            print("Error: pyproject.toml not found in current directory!", file=stderr)
            exit(1)

    @staticmethod
    def _validate_reserved_commands(scripts: dict[str, str | list[str]]) -> None:
        if "help" in scripts:
            error_text = color_service.bold_red("error")
            print(
                f"{error_text}: '{color_service.yellow('help')}' is a reserved command and cannot be used as a script name",
                file=stderr,
            )
            exit(1)

    @staticmethod
    def _get_command_from_argparse(parser: CustomArgumentParser) -> str:
        try:
            args = parser.parse_args()
            if not hasattr(args, "command") or not args.command:
                parser.print_help()
                exit(1)
            return args.command
        except SystemExit:
            raise
        except:  # noqa: E722
            parser.print_help()
            exit(1)


app = CliApplication(
    script_loader,
    version_loader,
    ArgumentParserBuilder(version_loader),
    ArgvParser(),
    CommandValidator(),
    CommandBuilder(),
    HelpCommandHandler(),
    CommandExecutorOrchestrator(command_executor),
)


def main() -> None:
    app.run()
