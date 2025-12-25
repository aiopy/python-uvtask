from pathlib import Path
from tomllib import loads


class PyProjectReader:
    def __init__(self, path: Path):
        self._path = path

    def exists(self) -> bool:
        return self._path.exists()

    def read(self) -> dict:
        if not self.exists():
            return {}
        with open(self._path) as file:
            return loads(file.read())


class ScriptValueParser:
    @staticmethod
    def parse(script_name: str, script_value: str | list[str] | dict) -> tuple[str | list[str], str]:
        if isinstance(script_value, str):
            return script_value, ""
        elif isinstance(script_value, list):
            return script_value, ""
        elif isinstance(script_value, dict):
            if "command" not in script_value:
                return str(script_value), ""
            cmd_value = script_value["command"]
            description = script_value.get("description", "")
            if isinstance(cmd_value, list):
                return cmd_value, description
            return cmd_value, description
        raise ValueError(f"Invalid script value: {script_value}")


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
                scripts[script_name] = str(command[0]) if command else ""
            else:
                scripts[script_name] = command
        return scripts

    def load_scripts_with_descriptions(
        self,
    ) -> tuple[dict[str, str | list[str]], dict[str, str]]:
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


pyproject_reader = PyProjectReader(Path("pyproject.toml"))

script_loader = ScriptLoader(
    reader=pyproject_reader,
    script_parser=ScriptValueParser(),
    section_reader=RunScriptSectionReader(),
)
version_loader = VersionLoader(pyproject_reader)
