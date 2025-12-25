from enum import StrEnum
from os import getenv
from sys import argv, stderr
from typing import ClassVar, Protocol


class ColorPreference(StrEnum):
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"

    @classmethod
    def from_string(cls, value: str) -> "ColorPreference":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.AUTO


class ColorFormatter(Protocol):
    def format(self, text: str, style: str) -> str: ...


class ColorSupportChecker(Protocol):
    def supports_color(self) -> bool: ...


class ColorPreferenceSource(Protocol):
    def get_preference(self) -> ColorPreference: ...


class EnvironmentColorSupportChecker:
    def supports_color(self) -> bool:
        no_color = getenv("NO_COLOR")
        if no_color is not None and no_color.lower().strip() not in ("0", "false"):
            return False

        force_color = getenv("FORCE_COLOR")
        if force_color is not None and force_color.lower().strip() not in ("0", "false"):
            return True

        if getenv("TERM", "").lower() == "dumb":
            return False

        return stderr.isatty()


class ColorSupportService:
    def __init__(
        self,
        preference: ColorPreference | None,
        environment_checker: ColorSupportChecker | None = None,
    ):
        self._preference = preference
        self._environment_checker = environment_checker or EnvironmentColorSupportChecker()

    def supports_color(self) -> bool:
        if self._preference == ColorPreference.ALWAYS:
            return True
        if self._preference == ColorPreference.NEVER:
            return False
        return self._environment_checker.supports_color()


class ArgvColorPreferenceSource:
    def get_preference(self) -> ColorPreference | None:
        for i, arg in enumerate(argv):
            if arg == "--color":
                if i + 1 < len(argv):
                    value = argv[i + 1]
                    return ColorPreference.from_string(value)
            elif arg.startswith("--color="):
                value = arg.split("=", 1)[1]
                return ColorPreference.from_string(value)
        return None


class EnvironmentColorPreferenceSource:
    def get_preference(self) -> ColorPreference | None:
        if getenv("NO_COLOR") is not None:
            return ColorPreference.NEVER
        if getenv("FORCE_COLOR") is not None:
            return ColorPreference.ALWAYS
        return None


class ColorPreferenceParser:
    def __init__(
        self,
        sources: list[ColorPreferenceSource] | None = None,
    ):
        self._sources = sources or [
            ArgvColorPreferenceSource(),
            EnvironmentColorPreferenceSource(),
        ]

    def parse(self) -> ColorPreference:
        for source in self._sources:
            preference = source.get_preference()
            if preference is not None:
                return preference
        return ColorPreference.AUTO


class AnsiColorFormatter:
    # ANSI escape codes
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    CYAN = "\x1b[36m"

    STYLES: ClassVar[dict[str, str]] = {
        "bold_red": f"{BOLD}{RED}",
        "bold_green": f"{BOLD}{GREEN}",
        "bold": BOLD,
        "bold_teal": f"{BOLD}{CYAN}",
        "teal": CYAN,
        "yellow": YELLOW,
        "green": GREEN,
    }

    def format(self, text: str, style: str) -> str:
        style_code = self.STYLES.get(style, "")
        if style_code:
            return f"{style_code}{text}{self.RESET}"
        return text


class NoOpColorFormatter:
    def format(self, text: str, style: str) -> str:
        return text


class ColorPreferenceManager:
    def __init__(self, parser: ColorPreferenceParser):
        self._preference: ColorPreference | None = None
        self._parser = parser
        self._support_service: ColorSupportService | None = None

    def set_preference(self, preference: ColorPreference) -> None:
        self._preference = preference
        self._support_service = None  # Reset cached service

    def set_preference_from_string(self, preference: str) -> None:
        self.set_preference(ColorPreference.from_string(preference))

    def get_preference(self) -> ColorPreference:
        if self._preference is None:
            self._preference = self._parser.parse()
        return self._preference

    def get_color_preference(self) -> str:
        return self.get_preference().value

    def supports_color(self) -> bool:
        if self._support_service is None:
            self._support_service = ColorSupportService(self.get_preference())
        return self._support_service.supports_color()

    def parse_color_from_argv(self) -> str:
        parser = ColorPreferenceParser()
        parsed_pref = parser.parse()
        self.set_preference(parsed_pref)
        return parsed_pref.value


class ColorService:
    def __init__(
        self,
        preference_manager: ColorPreferenceManager,
    ):
        self._preference_manager = preference_manager
        self._formatter: ColorFormatter | None = None

    def _get_formatter(self) -> ColorFormatter:
        if self._formatter is None:
            if self._preference_manager.supports_color():
                self._formatter = AnsiColorFormatter()
            else:
                self._formatter = NoOpColorFormatter()
        return self._formatter

    def format(self, text: str, style: str) -> str:
        return self._get_formatter().format(text, style)

    def bold_red(self, text: str) -> str:
        return self.format(text, "bold_red")

    def bold_green(self, text: str) -> str:
        return self.format(text, "bold_green")

    def bold(self, text: str) -> str:
        return self.format(text, "bold")

    def bold_teal(self, text: str) -> str:
        return self.format(text, "bold_teal")

    def teal(self, text: str) -> str:
        return self.format(text, "teal")

    def yellow(self, text: str) -> str:
        return self.format(text, "yellow")

    def green(self, text: str) -> str:
        return self.format(text, "green")


preference_manager = ColorPreferenceManager(ColorPreferenceParser())
color_service = ColorService(preference_manager)
