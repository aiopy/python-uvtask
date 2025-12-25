from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from sys import exit, stderr
from typing import ClassVar, NoReturn, Sequence

from uvtask.colors import color_service, preference_manager


class CommandMatcher:
    def find_similar(self, command: str, available_commands: list[str]) -> str | None:  # noqa: C901
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
    def _is_option_line(cls, line: str, stripped: str) -> bool:
        return bool(stripped and (stripped.startswith("-") or (line.startswith("  ") and not line.startswith("    ") and stripped)))

    @classmethod
    def _group_options(cls, lines: list[str]) -> list[list[str]]:
        options = []
        current_option = []

        for line in lines:
            stripped = line.strip()
            is_option_line = cls._is_option_line(line, stripped)

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

        return options

    @classmethod
    def _get_order(cls, option_lines: list[str]) -> int:
        sorted_opts = sorted(cls._ORDER_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        for line in option_lines:
            for opt, order in sorted_opts:
                if opt in line:
                    return order
        return 999

    @classmethod
    def _flatten_options(cls, options: list[list[str]]) -> list[str]:
        result = []
        for option in options:
            for line in option:
                if line.strip():
                    result.append(line)
        return result

    @classmethod
    def sort(cls, lines: list[str]) -> list[str]:
        options = cls._group_options(lines)
        options.sort(key=cls._get_order)
        return cls._flatten_options(options)


class HelpTextProcessor:
    def __init__(self, ansi_stripper: AnsiStripper):
        self._strip = ansi_stripper.strip

    def process_help_text(self, help_text: str) -> str:
        lines = help_text.split("\n")
        result = self._process_sections(lines)
        return self._add_section_spacing(result)

    def _process_section_header(self, line: str, stripped: str) -> str:
        if not preference_manager.supports_color():
            if "Global options" in stripped:
                return "Global options:"
            if "Commands" in stripped and ":" in stripped:
                return "Commands:"
        return line

    def _handle_global_options_start(self, result: list[str], processed_line: str) -> None:
        if result and result[-1].strip():
            result.append("")
        result.append(processed_line)

    def _handle_global_options_end(self, result: list[str], global_options_lines: list[str], line: str, stripped: str) -> None:
        sorted_lines = OptionSorter.sort(global_options_lines)
        result.extend(sorted_lines)
        if "Use `" in stripped or "for more information" in stripped.lower():
            result.append("")
        result.append(line)

    def _check_description_done(self, lines: list[str], i: int) -> bool:
        if i + 1 >= len(lines):
            return False
        next_line = lines[i + 1]
        stripped_next = self._strip(next_line)
        if "Commands" in stripped_next:
            return True
        if not next_line.strip() and i + 2 < len(lines):
            return "Commands" in self._strip(lines[i + 2])
        return False

    def _process_global_options_section(
        self, line: str, stripped: str, processed_line: str, in_global_options: bool, global_options_lines: list[str], result: list[str]
    ) -> tuple[bool, list[str]]:
        if "Global options" in stripped:
            in_global_options = True
            self._handle_global_options_start(result, processed_line)
        elif in_global_options and line.strip() and not line.startswith("  ") and not line.startswith("    "):
            in_global_options = False
            self._handle_global_options_end(result, global_options_lines, line, stripped)
            global_options_lines = []
        elif in_global_options:
            global_options_lines.append(line)
        return in_global_options, global_options_lines

    def _process_description_section(self, line: str, lines: list[str], i: int, description_done: bool, result: list[str]) -> tuple[bool, bool]:
        if description_done:
            return description_done, False
        if not line.strip() or "Commands" in self._strip(line):
            return description_done, False
        result.append(line)
        if self._check_description_done(lines, i):
            description_done = True
            if result and result[-1].strip():
                result.append("")
        return description_done, True

    def _process_commands_section(self, line: str, stripped: str, processed_line: str, usage_added: bool, result: list[str]) -> tuple[bool, bool]:
        if "Commands" in stripped and not usage_added:
            self._add_usage_line(result)
            result.append(processed_line)
            return True, True
        return usage_added, False

    def _process_sections(self, lines: list[str]) -> list[str]:
        result = []
        in_global_options = False
        global_options_lines = []
        description_done = False
        usage_added = False

        for i, line in enumerate(lines):
            stripped = self._strip(line)
            processed_line = self._process_section_header(line, stripped)

            new_in_global, new_global_lines = self._process_global_options_section(
                line, stripped, processed_line, in_global_options, global_options_lines, result
            )
            was_in_global = in_global_options
            in_global_options = new_in_global
            global_options_lines = new_global_lines

            if was_in_global or in_global_options:
                continue

            description_done, handled = self._process_description_section(line, lines, i, description_done, result)
            if handled:
                continue

            usage_added, handled = self._process_commands_section(line, stripped, processed_line, usage_added, result)
            if handled:
                continue

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

    def _is_epilog(self, stripped: str) -> bool:
        return bool("Use `" in stripped and ("uvtask help" in stripped or "for more details" in stripped.lower() or "for more information" in stripped.lower()))

    def _is_section_header(self, stripped: str) -> bool:
        return stripped.startswith("Usage:") or stripped in {"Commands:", "Global options:"}

    def _should_add_spacing_before(self, lines: list[str], i: int, new_lines: list[str]) -> bool:
        if i == 0:
            return False
        prev_line = lines[i - 1]
        return bool(prev_line.strip() and (not new_lines or new_lines[-1].strip()))

    def _should_keep_empty_line(self, lines: list[str], i: int) -> bool:
        if i + 1 >= len(lines):
            return False
        next_stripped = self._strip(lines[i + 1])
        next_is_epilog = self._is_epilog(next_stripped)
        next_is_section = self._is_section_header(next_stripped)
        return next_is_epilog or next_is_section

    def _add_section_spacing(self, lines: list[str]) -> str:
        new_lines = []
        for i, line in enumerate(lines):
            stripped = self._strip(line)
            is_section_header = self._is_section_header(stripped)
            is_epilog = self._is_epilog(stripped)

            if is_section_header and self._should_add_spacing_before(lines, i, new_lines):
                new_lines.append("")

            if is_epilog:
                if self._should_add_spacing_before(lines, i, new_lines):
                    new_lines.append("")
                new_lines.append(line)
            elif not line.strip():
                if self._should_keep_empty_line(lines, i):
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

    def _calculate_max_command_width(self, action: argparse._SubParsersAction) -> int:
        max_cmd_width = 24
        for choice in action.choices.keys():
            clean_choice = self._ansi_stripper.strip(choice)
            max_cmd_width = max(max_cmd_width, len(clean_choice))
        return max_cmd_width + 2

    def _extract_choices_help(self, action: argparse._SubParsersAction) -> dict[str, str]:
        choices_help = {}
        if hasattr(action, '_choices_actions'):
            for choice_action in action._choices_actions:
                if choice_action.help:
                    choices_help[choice_action.dest] = choice_action.help
        return choices_help

    def _format_command_line(self, choice: str, help_text: str, width: int) -> list[str]:
        cmd_name = color_service.bold_teal(choice) if preference_manager.supports_color() else choice
        clean_cmd = self._ansi_stripper.strip(cmd_name)

        if len(clean_cmd) < width and help_text:
            aligned_cmd = cmd_name + " " * (width - len(clean_cmd))
            return [f"  {aligned_cmd}{help_text}"]
        parts = [f"  {cmd_name}"]
        if help_text:
            parts.append(f"    {help_text}")
        return parts

    def _format_subparsers(self, action: argparse._SubParsersAction) -> str:
        width = self._calculate_max_command_width(action)
        choices_help = self._extract_choices_help(action)

        parts = []
        for choice, _ in action.choices.items():
            help_text = choices_help.get(choice, "")
            parts.extend(self._format_command_line(choice, help_text, width))

        return "\n".join(parts) + "\n" if parts else ""

    def _get_custom_help_text(self, option_strings: Sequence[str]) -> str | None:
        help_map = {
            ("--help", "-h"): "Display the concise help for this command",
            ("--quiet", "-q"): "Use quiet output",
            ("--verbose", "-v"): "Use verbose output",
            ("--version", "-V"): "Display the uvtask version",
        }
        for options, text in help_map.items():
            if any(opt in option_strings for opt in options):
                return text
        return None

    def _get_help_text(self, action: argparse.Action) -> str:
        help_text = self._expand_help(action) if action.help else ""
        help_text = help_text.replace("%(default)s", str(action.default))
        help_text = help_text.replace("%(prog)s", self._prog)

        if action.option_strings:
            custom_help = self._get_custom_help_text(action.option_strings)
            if custom_help:
                return custom_help

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
