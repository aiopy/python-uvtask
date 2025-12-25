from sys import exit, stderr

from uvtask.colors import color_service, preference_manager
from uvtask.executor import CommandExecutor
from uvtask.formatters import CommandMatcher, CustomArgumentParser


class CommandValidator:
    def __init__(self, command_matcher: CommandMatcher | None = None):
        self._matcher = command_matcher or CommandMatcher()

    def validate_exists(self, command_name: str, scripts: dict[str, str | list[str]]) -> None:
        if command_name not in scripts:
            error_text = color_service.bold_red("error")
            usage_text = color_service.bold_green("Usage:")
            prog_text = color_service.bold_teal("uvtask")
            options_text = color_service.teal("[OPTIONS]")
            command_text = color_service.teal("<COMMAND>")
            help_text = color_service.bold_teal("--help")

            print(f"{error_text}: unrecognized subcommand '{color_service.yellow(command_name)}'", file=stderr)

            available_commands = list(scripts.keys())
            similar = self._matcher.find_similar(command_name, available_commands)
            if similar:
                tip_text = color_service.yellow("tip")
                similar_cmd = color_service.yellow(f"'{similar}'")
                print(f"\n  {tip_text}: a similar subcommand exists: {similar_cmd}", file=stderr)

            print(f"\n{usage_text} {prog_text} {options_text} {command_text}", file=stderr)
            print(f"\nFor more information, try '{help_text}'.", file=stderr)
            exit(1)


class CommandResolver:
    @staticmethod
    def resolve_command_references(command: str, all_scripts: dict[str, str | list[str]], visited: set[str] | None = None) -> list[str]:
        if visited is None:
            visited = set()

        if command in visited:
            raise ValueError(f"Circular reference detected: {' -> '.join(visited)} -> {command}")

        if command not in all_scripts:
            return [command]

        visited.add(command)
        referenced_script = all_scripts[command]

        if isinstance(referenced_script, str):
            result = CommandResolver.resolve_command_references(referenced_script, all_scripts, visited.copy())
        elif isinstance(referenced_script, list):
            result = []
            for cmd in referenced_script:
                if cmd in all_scripts:
                    result.extend(CommandResolver.resolve_command_references(cmd, all_scripts, visited.copy()))
                else:
                    result.append(cmd)
        else:
            result = [str(referenced_script)]

        visited.remove(command)
        return result

    @staticmethod
    def resolve_list_references(commands: list[str], all_scripts: dict[str, str | list[str]]) -> list[str]:
        resolved = []
        for cmd in commands:
            if cmd in all_scripts:
                resolved.extend(CommandResolver.resolve_command_references(cmd, all_scripts))
            else:
                resolved.append(cmd)
        return resolved


class CommandBuilder:
    def __init__(self, resolver: CommandResolver | None = None):
        self._resolver = resolver or CommandResolver()

    def build_commands(self, script: str | list[str], script_args: list[str], all_scripts: dict[str, str | list[str]] | None = None) -> list[str]:
        script_args_str = " ".join(script_args) if script_args else ""

        if isinstance(script, str):
            if all_scripts and script in all_scripts:
                resolved = self._resolver.resolve_command_references(script, all_scripts)
                return [f"{cmd} {script_args_str}".strip() for cmd in resolved]
            return [f"{script} {script_args_str}".strip()]
        elif isinstance(script, list):
            if all_scripts:
                resolved = self._resolver.resolve_list_references(script, all_scripts)
                return [f"{cmd} {script_args_str}".strip() for cmd in resolved]
            return [f"{cmd} {script_args_str}".strip() for cmd in script]
        else:
            raise ValueError(f"Invalid script format: {script}")


class HelpCommandHandler:
    def __init__(self, command_matcher: CommandMatcher | None = None):
        self._matcher = command_matcher or CommandMatcher()

    def handle_help(
        self,
        help_command_name: str | None,
        scripts: dict[str, str | list[str]],
        script_descriptions: dict[str, str],
        parser: "CustomArgumentParser",  # type: ignore
    ) -> None:
        if help_command_name:
            self._show_command_help(help_command_name, scripts, script_descriptions)
        else:
            self._show_general_help(parser)

    def _show_command_help(self, command_name: str, scripts: dict[str, str | list[str]], script_descriptions: dict[str, str]) -> None:
        if command_name not in scripts:
            error_text = color_service.bold_red("error")
            print(f"{error_text}: unknown command '{color_service.yellow(command_name)}'", file=stderr)

            available_commands = list(scripts.keys())
            similar = self._matcher.find_similar(command_name, available_commands)
            if similar:
                tip_text = color_service.yellow("tip")
                similar_cmd = color_service.yellow(f"'{similar}'")
                print(f"\n  {tip_text}: a similar command exists: {similar_cmd}", file=stderr)

            exit(1)

        description = script_descriptions.get(command_name, "")
        command_cmd = color_service.bold_teal(command_name) if preference_manager.supports_color() else command_name

        if description:
            print(description)
        else:
            no_desc_text = color_service.yellow("No description provided") if preference_manager.supports_color() else "No description provided"
            print(no_desc_text)
            print()
            print("To add a description, update your pyproject.toml:")
            print()

            actual_command = scripts.get(command_name, "...")
            # Handle both str and list[str] cases
            if isinstance(actual_command, list):
                actual_command = actual_command[0] if actual_command else "..."
            escaped_command = actual_command.replace('"', '\\"').replace('\n', '\\n')
            if len(actual_command) > 50 or '\n' in actual_command:
                example_cmd = (
                    color_service.bold_teal(f'  {command_name} = {{ command = "...", description = "Your description here" }}')
                    if preference_manager.supports_color()
                    else f'  {command_name} = {{ command = "...", description = "Your description here" }}'
                )
            else:
                example_cmd = (
                    color_service.bold_teal(f'  {command_name} = {{ command = "{escaped_command}", description = "Your description here" }}')
                    if preference_manager.supports_color()
                    else f'  {command_name} = {{ command = "{escaped_command}", description = "Your description here" }}'
                )
                print(example_cmd)

        print()
        usage_text = color_service.bold_green("Usage:") if preference_manager.supports_color() else "Usage:"
        prog_text = color_service.bold_teal("uvtask") if preference_manager.supports_color() else "uvtask"
        options_text = color_service.teal("[OPTIONS]") if preference_manager.supports_color() else "[OPTIONS]"
        command_arg_text = color_service.teal("[COMMAND]") if preference_manager.supports_color() else "[COMMAND]"
        print(f"{usage_text} {prog_text} {command_cmd} {options_text} {command_arg_text}")
        print()
        help_cmd_text = color_service.bold("uvtask help <command>") if preference_manager.supports_color() else "uvtask help <command>"
        print(f"Use `{help_cmd_text}` for more information on a specific command.")
        print()
        exit(0)

    def _show_general_help(self, parser: "CustomArgumentParser") -> None:
        original_epilog = parser.epilog
        help_cmd_text = color_service.bold("uvtask help <command>")
        parser.epilog = f"\n\nUse `{help_cmd_text}` for more information on a specific command."
        parser.print_help()
        print()
        parser.epilog = original_epilog
        exit(0)


class CommandExecutorOrchestrator:
    def __init__(
        self,
        executor: CommandExecutor,
        verbose_output: "VerboseOutputHandler" | None = None,
    ):
        self._executor = executor
        self._verbose = verbose_output or VerboseOutputHandler()

    def execute(
        self,
        command_name: str,
        main_commands: list[str],
        pre_hooks: list[str],
        post_hooks: list[str],
        quiet_count: int,
        verbose_count: int,
    ) -> None:
        try:
            self._verbose.show_execution_info(command_name, main_commands, pre_hooks, post_hooks, verbose_count)

            for hook_command in pre_hooks:
                exit_code = self._executor.execute(hook_command, quiet_count, verbose_count)
                if exit_code != 0:
                    self._verbose.show_hook_failure("Pre-hook", exit_code, verbose_count)
                    exit(exit_code)

            main_exit_code = 0
            for i, main_command in enumerate(main_commands):
                if verbose_count > 0 and len(main_commands) > 1:
                    print(
                        color_service.bold_green(f"Executing command {i + 1}/{len(main_commands)}"),
                        file=stderr,
                    )
                exit_code = self._executor.execute(main_command, quiet_count, verbose_count)
                if exit_code != 0:
                    main_exit_code = exit_code
                    self._verbose.show_command_failure(exit_code, verbose_count)
                    break

            for hook_command in post_hooks:
                hook_exit_code = self._executor.execute(hook_command, quiet_count, verbose_count)
                if main_exit_code == 0 and hook_exit_code != 0:
                    main_exit_code = hook_exit_code
                    self._verbose.show_hook_failure("Post-hook", hook_exit_code, verbose_count)

            self._verbose.show_final_exit_code(main_exit_code, verbose_count)
            exit(main_exit_code)
        except KeyboardInterrupt:
            if verbose_count > 0:
                print(color_service.bold_red("Interrupted by user"), file=stderr)
            exit(130)


class VerboseOutputHandler:
    @staticmethod
    def show_execution_info(
        command_name: str,
        main_commands: list[str],
        pre_hooks: list[str],
        post_hooks: list[str],
        verbose_count: int,
    ) -> None:
        if verbose_count > 0:
            print(color_service.bold_green(f"Command: {command_name}"), file=stderr)
            if pre_hooks:
                print(color_service.bold_green(f"Pre-hooks: {len(pre_hooks)}"), file=stderr)
            if len(main_commands) > 1:
                print(color_service.bold_green(f"Commands to execute: {len(main_commands)}"), file=stderr)
            if post_hooks:
                print(color_service.bold_green(f"Post-hooks: {len(post_hooks)}"), file=stderr)
            print("", file=stderr)

    @staticmethod
    def show_hook_failure(hook_type: str, exit_code: int, verbose_count: int) -> None:
        if verbose_count > 0:
            print(color_service.bold_red(f"{hook_type} failed with exit code {exit_code}"), file=stderr)

    @staticmethod
    def show_command_failure(exit_code: int, verbose_count: int) -> None:
        if verbose_count > 0:
            print(color_service.bold_red(f"Command failed with exit code {exit_code}"), file=stderr)

    @staticmethod
    def show_final_exit_code(exit_code: int, verbose_count: int) -> None:
        if verbose_count > 0:
            final_exit_text = (
                color_service.bold_green(f"Final exit code: {exit_code}") if exit_code == 0 else color_service.bold_red(f"Final exit code: {exit_code}")
            )
            print(final_exit_text, file=stderr)
