from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tomllib import loads

from uvtask.types import ScriptsMapping

MAX_PYPROJECT_BYTES = 5 * 1024 * 1024


class PyProjectReader:
    def __init__(self, path: Path, max_bytes: int = MAX_PYPROJECT_BYTES):
        self._path = path
        self._max_bytes = max_bytes
        self._cache: dict | None = None

    def exists(self) -> bool:
        return self._path.is_file()

    def read(self) -> dict:
        if self._cache is not None:
            return self._cache

        try:
            with open(self._path, "rb") as file:
                content = file.read(self._max_bytes + 1)
        except OSError:
            return {}

        if len(content) > self._max_bytes:
            raise ValueError(f"{self._path} is larger than {self._max_bytes} bytes")

        self._cache = loads(content.decode())
        return self._cache


class ScriptValueParser:
    @staticmethod
    def _parse_command(script_name: str, cmd_value: object) -> str | list[str]:
        if isinstance(cmd_value, str):
            return cmd_value
        if isinstance(cmd_value, list):
            commands: list[str] = []
            for item in cmd_value:
                if not isinstance(item, str):
                    raise ValueError(f"Invalid script value for '{script_name}': list entries must be strings")
                commands.append(item)
            return commands
        raise ValueError(f"Invalid script value for '{script_name}': expected a string or a list of strings")

    @staticmethod
    def parse(script_name: str, script_value: str | list[str] | dict) -> tuple[str | list[str], str]:
        if isinstance(script_value, str | list):
            return ScriptValueParser._parse_command(script_name, script_value), ""
        if isinstance(script_value, dict):
            if "command" not in script_value:
                raise ValueError(f"Invalid script value for '{script_name}': table is missing a 'command' key")
            description = script_value.get("description", "")
            if not isinstance(description, str):
                raise ValueError(f"Invalid script value for '{script_name}': 'description' must be a string")
            return ScriptValueParser._parse_command(script_name, script_value["command"]), description
        raise ValueError(f"Invalid script value for '{script_name}': expected a string, a list of strings, or a table")


class RunScriptSectionReader:
    @staticmethod
    def get_run_script_section(tool_section: dict) -> dict:
        if "uvtask" in tool_section and "run-script" in tool_section["uvtask"]:
            return tool_section["uvtask"]["run-script"]
        return tool_section.get("run-script", {})


class ScriptLoader:
    def __init__(
        self,
        reader: PyProjectReader,
        script_parser: ScriptValueParser,
        section_reader: RunScriptSectionReader,
    ):
        self._reader = reader
        self._parser = script_parser
        self._section_reader = section_reader

    def load_scripts(self) -> dict[str, str]:
        if not self._reader.exists():
            return {}
        data = self._reader.read()
        tool_section = data.get("tool", {})
        run_script = self._section_reader.get_run_script_section(tool_section)
        # Convert all to strings for backward compatibility
        scripts = {}
        for script_name, script_value in run_script.items():
            command, _ = self._parser.parse(script_name, script_value)
            if isinstance(command, list):
                scripts[script_name] = command[0] if command else ""
            else:
                scripts[script_name] = command
        return scripts

    def load_scripts_with_descriptions(
        self,
    ) -> tuple[ScriptsMapping, dict[str, str]]:
        if not self._reader.exists():
            return {}, {}

        data = self._reader.read()
        tool_section = data.get("tool", {})
        run_script = self._section_reader.get_run_script_section(tool_section)

        scripts: dict[str, str | list[str]] = {}
        descriptions: dict[str, str] = {}

        for script_name, script_value in run_script.items():
            command, description = self._parser.parse(script_name, script_value)
            scripts[script_name] = command
            descriptions[script_name] = description

        return scripts, descriptions


class VersionLoader:
    def __init__(self, reader: PyProjectReader):
        self._reader = reader

    def get_version(self) -> str:
        if not self._reader.exists():
            return "unknown"
        data = self._reader.read()
        return data.get("project", {}).get("version", "unknown")

    def get_package_version(self) -> str:
        try:
            return version("uvtask")
        except PackageNotFoundError:
            return "unknown"


pyproject_reader = PyProjectReader(Path("pyproject.toml"))

script_loader = ScriptLoader(
    reader=pyproject_reader,
    script_parser=ScriptValueParser(),
    section_reader=RunScriptSectionReader(),
)
version_loader = VersionLoader(pyproject_reader)
