from pathlib import Path

import pytest

from uvtask.config import (
    PyProjectReader,
    RunScriptSectionReader,
    ScriptLoader,
    ScriptValueParser,
    VersionLoader,
)


class TestPyProjectReader:
    def test_exists_true(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test'")
        reader = PyProjectReader(pyproject_path)
        assert reader.exists() is True

    def test_exists_false(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "nonexistent.toml"
        reader = PyProjectReader(pyproject_path)
        assert reader.exists() is False

    def test_read_existing_file(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test'\nversion = '1.0.0'")
        reader = PyProjectReader(pyproject_path)
        data = reader.read()
        assert data["project"]["name"] == "test"
        assert data["project"]["version"] == "1.0.0"

    def test_read_nonexistent_file(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "nonexistent.toml"
        reader = PyProjectReader(pyproject_path)
        data = reader.read()
        assert data == {}


class TestScriptValueParser:
    def test_parse_string(self) -> None:
        command, description = ScriptValueParser.parse("test", "echo hello")
        assert command == "echo hello"
        assert description == ""

    def test_parse_list(self) -> None:
        command, description = ScriptValueParser.parse("test", ["echo hello", "echo world"])
        assert command == ["echo hello", "echo world"]
        assert description == ""

    def test_parse_dict_with_command_string(self) -> None:
        command, description = ScriptValueParser.parse("test", {"command": "echo hello", "description": "Test command"})
        assert command == "echo hello"
        assert description == "Test command"

    def test_parse_dict_with_multiline_command(self) -> None:
        multiline_cmd = """python3 -c "
from glob import iglob
from shutil import rmtree

for pathname in ['./build', './*.egg-info']:
  for path in iglob(pathname, recursive=True):
    rmtree(path, ignore_errors=True)
"
"""
        command, description = ScriptValueParser.parse("clean", {"command": multiline_cmd, "description": "Clean build artifacts"})
        assert "\n" in command
        assert "python3 -c" in command
        assert "from glob import iglob" in command
        assert description == "Clean build artifacts"

    def test_parse_dict_with_command_list(self) -> None:
        command, description = ScriptValueParser.parse("test", {"command": ["echo hello", "echo world"], "description": "Test commands"})
        assert command == ["echo hello", "echo world"]
        assert description == "Test commands"

    def test_parse_dict_without_description(self) -> None:
        command, description = ScriptValueParser.parse("test", {"command": "echo hello"})
        assert command == "echo hello"
        assert description == ""

    def test_parse_dict_without_command(self) -> None:
        command, description = ScriptValueParser.parse("test", {"description": "Test"})
        assert command == "{'description': 'Test'}"
        assert description == ""

    def test_parse_invalid_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid script value"):
            ScriptValueParser.parse("test", 123)  # type: ignore[arg-type]


class TestRunScriptSectionReader:
    def test_get_uvtask_namespace(self) -> None:
        tool_section = {"uvtask": {"run-script": {"test": "echo test"}}}
        result = RunScriptSectionReader.get_run_script_section(tool_section)
        assert result == {"test": "echo test"}

    def test_get_tool_namespace(self) -> None:
        tool_section = {"run-script": {"test": "echo test"}}
        result = RunScriptSectionReader.get_run_script_section(tool_section)
        assert result == {"test": "echo test"}

    def test_uvtask_takes_precedence(self) -> None:
        tool_section = {
            "uvtask": {"run-script": {"test": "uvtask version"}},
            "run-script": {"test": "tool version"},
        }
        result = RunScriptSectionReader.get_run_script_section(tool_section)
        assert result == {"test": "uvtask version"}

    def test_empty_section(self) -> None:
        tool_section = {}
        result = RunScriptSectionReader.get_run_script_section(tool_section)
        assert result == {}


class TestScriptLoader:
    def test_load_scripts_with_descriptions(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path = temp_dir / "nonexistent.toml"
        reader = PyProjectReader(pyproject_path)
        loader = ScriptLoader(reader, ScriptValueParser(), RunScriptSectionReader())
        scripts, descriptions = loader.load_scripts_with_descriptions()
        assert scripts == {}
        assert descriptions == {}


class TestVersionLoader:
    def test_get_version(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path = temp_dir / "nonexistent.toml"
        reader = PyProjectReader(pyproject_path)
        loader = VersionLoader(reader)
        assert loader.get_version() == "unknown"
