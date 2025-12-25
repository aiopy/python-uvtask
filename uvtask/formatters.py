import argparse
import re
from collections.abc import Iterable
from sys import exit, stderr
from typing import ClassVar, NoReturn

from uvtask.colors import color_service, preference_manager


class CommandMatcher:
    def find_similar(self, command: str, available_commands: list[str]) -> str | None:
        if not available_commands:
            return None

        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]

        def similarity(cmd1: str, cmd2: str) -> float:
            cmd1_lower = cmd1.lower()
            cmd2_lower = cmd2.lower()
            if cmd1_lower == cmd2_lower:
                return 1.0
            if cmd1_lower.startswith(cmd2_lower) or cmd2_lower.startswith(cmd1_lower):
                return 0.7
            if cmd1_lower in cmd2_lower or cmd2_lower in cmd1_lower:
                return 0.6
            max_len = max(len(cmd1), len(cmd2))
            if max_len == 0:
                return 0.0
            distance = levenshtein_distance(cmd1_lower, cmd2_lower)
            return 1.0 - (distance / max_len)

        best_match = None
        best_score = 0.0
        for available_cmd in available_commands:
            score = similarity(command, available_cmd)
            if score > best_score and score > 0.4:
                best_score = score
                best_match = available_cmd
        return best_match


class AnsiStripper:
    _ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    @classmethod
    def strip(cls, text: str) -> str:
        return cls._ansi_escape.sub('', text)


class OptionSorter:
    _ORDER_MAP: ClassVar[dict[str, int]] = {
        "-q": 0,
        "--quiet": 0,
        "-v": 1,
        "--verbose": 1,
        "--color": 2,
        "--no-hooks": 3,
        "--ignore-scripts": 3,
        "-V": 4,
        "--version": 4,
        "-h": 5,
        "--help": 5,
    }

    @classmethod
    def sort(cls, lines: list[str]) -> list[str]:
        options = []
        current_option = []

        for line in lines:
            stripped = line.strip()
            is_option_line = stripped and (stripped.startswith("-") or (line.startswith("  ") and not line.startswith("    ") and stripped))

            if is_option_line:
                if current_option:
                    options.append(current_option)
                current_option = [line]
            elif current_option:
                current_option.append(line)
            else:
                if current_option:
                    options.append(current_option)
                    current_option = []
                if stripped:
                    options.append([line])

        if current_option:
            options.append(current_option)

        def get_order(option_lines: list[str]) -> int:
            for line in option_lines:
                sorted_opts = sorted(cls._ORDER_MAP.items(), key=lambda x: len(x[0]), reverse=True)
                for opt, order in sorted_opts:
                    if opt in line:
                        return order
            return 999

        options.sort(key=get_order)

        result = []
        for option in options:
            for line in option:
                if line.strip():
                    result.append(line)
        return result


class HelpTextProcessor:
    def __init__(self, ansi_stripper: AnsiStripper):
        self._strip = ansi_stripper.strip

    def process_help_text(self, help_text: str) -> str:
        lines = help_text.split("\n")
        result = self._process_sections(lines)
        return self._add_section_spacing(result)

    def _process_sections(self, lines: list[str]) -> list[str]:
        result = []
        in_global_options = False
        global_options_lines = []
        description_done = False
        usage_added = False

        for i, line in enumerate(lines):
            stripped = self._strip(line)

            # Handle color stripping for section headers
            processed_line = line
            if not preference_manager.supports_color():
                if "Global options" in stripped:
                    processed_line = "Global options:"
                elif "Commands" in stripped and ":" in stripped:
                    processed_line = "Commands:"

            # Process Global options section
            if "Global options" in stripped:
                in_global_options = True
                if result and result[-1].strip():
                    result.append("")
                result.append(processed_line)
            elif in_global_options and line.strip() and not line.startswith("  ") and not line.startswith("    "):
                in_global_options = False
                sorted_lines = OptionSorter.sort(global_options_lines)
                result.extend(sorted_lines)
                global_options_lines = []
                if "Use `" in stripped or "for more information" in stripped.lower():
                    result.append("")
                result.append(line)
            elif in_global_options:
                global_options_lines.append(line)
            # Handle description and Usage line
            elif not description_done and line.strip() and "Commands" not in self._strip(line):
                result.append(line)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    stripped_next = self._strip(next_line)
                    if "Commands" in stripped_next or (not next_line.strip() and i + 2 < len(lines) and "Commands" in self._strip(lines[i + 2])):
                        description_done = True
                        if result and result[-1].strip():
                            result.append("")
            elif "Commands" in self._strip(line) and not usage_added:
                self._add_usage_line(result)
                usage_added = True
                result.append(processed_line)
            else:
                result.append(line)

        if global_options_lines:
            sorted_lines = OptionSorter.sort(global_options_lines)
            result.extend(sorted_lines)

        return result

    def _add_usage_line(self, result: list[str]) -> None:
        usage_text = color_service.bold_green("Usage:") if preference_manager.supports_color() else "Usage:"
        prog_text = color_service.bold_teal("uvtask") if preference_manager.supports_color() else "uvtask"
        options_text = color_service.teal("[OPTIONS]") if preference_manager.supports_color() else "[OPTIONS]"
        command_text = color_service.teal("<COMMAND>") if preference_manager.supports_color() else "<COMMAND>"
        result.append(f"{usage_text} {prog_text} {options_text} {command_text}")
        result.append("")

    def _add_section_spacing(self, lines: list[str]) -> str:
        new_lines = []
        for i, line in enumerate(lines):
            stripped = self._strip(line)
            is_usage = stripped.startswith("Usage:")
            is_commands = stripped == "Commands:"
            is_global_options = stripped == "Global options:"
            is_epilog = "Use `" in stripped and (
                "uvtask help" in stripped or "for more details" in stripped.lower() or "for more information" in stripped.lower()
            )

            is_section_header = is_usage or is_commands or is_global_options

            if is_section_header and i > 0:
                prev_line = lines[i - 1] if i > 0 else ""
                if prev_line.strip() and (not new_lines or new_lines[-1].strip()):
                    new_lines.append("")

            if is_epilog:
                if i > 0 and lines[i - 1].strip() and (not new_lines or new_lines[-1].strip()):
                    new_lines.append("")
                new_lines.append(line)
            elif not line.strip():
                if i + 1 < len(lines):
                    next_stripped = self._strip(lines[i + 1])
                    next_is_epilog = "Use `" in next_stripped and (
                        "uvtask help" in next_stripped or "for more details" in next_stripped.lower() or "for more information" in next_stripped.lower()
                    )
                    next_is_section = next_stripped.startswith("Usage:") or next_stripped in {"Commands:", "Global options:"}
                    if next_is_epilog or next_is_section:
                        new_lines.append(line)
            else:
                new_lines.append(line)

        return "\n".join(new_lines)


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ansi_stripper = AnsiStripper()
        self._help_processor = HelpTextProcessor(self._ansi_stripper)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            return self._metavar_formatter(action, default)(1)[0]

        parts = []
        for option_string in action.option_strings:
            formatted = color_service.bold_teal(option_string) if preference_manager.supports_color() else option_string
            parts.append(formatted)

        result = ", ".join(parts)

        # Add "..." for count actions
        is_count_action = isinstance(action, argparse._CountAction)
        if is_count_action and any(opt in ["-q", "--quiet", "-v", "--verbose"] for opt in action.option_strings):
            result += "..."

        # Add metavar
        metavar_str = self._get_metavar_str(action)
        if metavar_str:
            if "--color" in action.option_strings:
                formatted_metavar = f"<{color_service.teal(metavar_str) if preference_manager.supports_color() else metavar_str}>"
                result = f"{result} {formatted_metavar}"
            else:
                result = f"{result} {metavar_str}"

        return result

    def _get_metavar_str(self, action: argparse.Action) -> str:
        if action.metavar is not None:
            # metavar can be str or tuple[str, ...], convert tuple to str
            if isinstance(action.metavar, tuple):
                return action.metavar[0] if action.metavar else ""
            return action.metavar
        if action.choices is not None:
            if "--color" in action.option_strings:
                return "COLOR_CHOICE"
            return self._format_args(action, self._get_default_metavar_for_optional(action))
        return self._format_args(action, self._get_default_metavar_for_optional(action))

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            return self._format_subparsers(action)

        help_text = self._get_help_text(action)
        invocation = self._format_action_invocation(action)
        clean_invocation = self._ansi_stripper.strip(invocation)
        width = 30

        if len(clean_invocation) < width:
            aligned_invocation = invocation + " " * (width - len(clean_invocation))
            return f"  {aligned_invocation}{help_text}\n" if help_text else f"  {invocation}\n"
        else:
            if help_text:
                return f"  {invocation}\n    {help_text}\n"
            return f"  {invocation}\n"

    def _format_subparsers(self, action: argparse._SubParsersAction) -> str:
        max_cmd_width = 24
        for choice in action.choices.keys():
            clean_choice = self._ansi_stripper.strip(choice)
            max_cmd_width = max(max_cmd_width, len(clean_choice))
        width = max_cmd_width + 2

        choices_help = {}
        if hasattr(action, '_choices_actions'):
            for choice_action in action._choices_actions:
                if choice_action.help:
                    choices_help[choice_action.dest] = choice_action.help

        parts = []
        for choice, _ in action.choices.items():
            help_text = choices_help.get(choice, "")
            cmd_name = color_service.bold_teal(choice) if preference_manager.supports_color() else choice
            clean_cmd = self._ansi_stripper.strip(cmd_name)

            if len(clean_cmd) < width and help_text:
                aligned_cmd = cmd_name + " " * (width - len(clean_cmd))
                parts.append(f"  {aligned_cmd}{help_text}")
            else:
                parts.append(f"  {cmd_name}")
                if help_text:
                    parts.append(f"    {help_text}")

        return "\n".join(parts) + "\n" if parts else ""

    def _get_help_text(self, action: argparse.Action) -> str:
        help_text = self._expand_help(action) if action.help else ""
        help_text = help_text.replace("%(default)s", str(action.default))
        help_text = help_text.replace("%(prog)s", self._prog)

        if action.option_strings:
            if "--help" in action.option_strings or "-h" in action.option_strings:
                return "Display the concise help for this command"
            elif "--quiet" in action.option_strings or "-q" in action.option_strings:
                return "Use quiet output"
            elif "--verbose" in action.option_strings or "-v" in action.option_strings:
                return "Use verbose output"
            elif "--version" in action.option_strings or "-V" in action.option_strings:
                return "Display the uvtask version"

        return help_text

    def _format_usage(self, usage: str | None, actions: Iterable[argparse.Action], groups: Iterable[argparse._ArgumentGroup], prefix: str | None) -> str:
        if usage is None:
            usage = ""
        if prefix is None:
            prefix = "Usage: "
        usage_text = color_service.bold_green(prefix) if preference_manager.supports_color() else prefix
        return f"{usage_text}{usage}"

    def add_usage(self, usage: str | None, actions: Iterable[argparse.Action], groups: Iterable[argparse._ArgumentGroup], prefix: str | None = None) -> None:
        if usage is not None:
            text = self._format_usage(usage, actions, groups, prefix)
            self._add_item(self._format_text, [text])

    def start_section(self, heading: str | None) -> None:
        if heading is None:
            heading = ""
        if heading == "options":
            heading = color_service.bold_green("Global options") if preference_manager.supports_color() else "Global options"
        elif heading == "positional arguments":
            heading = color_service.bold_green("Commands") if preference_manager.supports_color() else "Commands"
        super().start_section(heading)

    def format_help(self) -> str:
        help_text = super().format_help()
        return self._help_processor.process_help_text(help_text)


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", CustomHelpFormatter)
        super().__init__(*args, **kwargs)
        self._command_matcher = CommandMatcher()

    def error(self, message: str) -> NoReturn:
        color_pref = preference_manager.parse_color_from_argv()
        preference_manager.set_preference_from_string(color_pref)

        if "invalid choice:" in message:
            match = re.search(r"invalid choice: '([^']+)'", message)
            if match:
                command = match.group(1)
                error_text = color_service.bold_red("error")
                usage_text = color_service.bold_green("Usage:")
                prog_text = color_service.bold_teal(self.prog)
                options_text = color_service.teal("[OPTIONS]")
                command_text = color_service.teal("<COMMAND>")
                help_text = color_service.bold_teal("--help")

                available_commands = []
                if hasattr(self, '_subparsers') and self._subparsers is not None:
                    for action in self._subparsers._actions:
                        if isinstance(action, argparse._SubParsersAction):
                            available_commands = list(action.choices.keys())
                            break

                print(f"{error_text}: unrecognized subcommand '{color_service.yellow(command)}'", file=stderr)

                similar = self._command_matcher.find_similar(command, available_commands)
                if similar:
                    tip_text = color_service.green("tip")
                    similar_cmd = color_service.green(f"'{similar}'")
                    print(f"\n  {tip_text}: a similar subcommand exists: {similar_cmd}", file=stderr)

                print(f"\n{usage_text} {prog_text} {options_text} {command_text}", file=stderr)
                print(f"\nFor more information, try '{help_text}'.", file=stderr)
                exit(1)
        super().error(message)


command_matcher = CommandMatcher()
