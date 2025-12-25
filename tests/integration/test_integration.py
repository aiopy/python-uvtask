import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


def run_uvtask(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT.absolute())
    env["PYTHONUNBUFFERED"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "uvtask", *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )
    return result


class TestBasicExecution:
    def test_execute_simple_command(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text('[tool.run-script]\ntest = "echo hello"\n')

        result = run_uvtask(["test"], temp_dir)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_execute_command_with_args(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text('[tool.run-script]\ngreet = "echo"\n')

        result = run_uvtask(["greet", "hello", "world"], temp_dir)
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert "world" in result.stdout

    def test_execute_multiple_commands(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text('[tool.run-script]\nmulti = ["echo first", "echo second"]\n')

        result = run_uvtask(["multi"], temp_dir)
        assert result.returncode == 0
        assert "first" in result.stdout
        assert "second" in result.stdout


class TestHooks:
    def test_pre_and_post_hooks(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text('[tool.run-script]\npre-test = "echo pre"\ntest = "echo main"\npost-test = "echo post"\n')

        result = run_uvtask(["test"], temp_dir)
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "pre" in output
        assert "main" in output
        assert "post" in output

    def test_no_hooks_flag(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_path.write_text('[tool.run-script]\npre-test = "echo pre"\ntest = "echo main"\npost-test = "echo post"\n')

        result = run_uvtask(["--no-hooks", "test"], temp_dir)
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "main" in output
        assert "pre" not in output
        assert "post" not in output


class TestHelp:
    def test_help_command(self, pyproject_toml: Path) -> None:
        result = run_uvtask(["help"], pyproject_toml.parent)
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "Usage:" in result.stderr

    def test_help_specific_command(self, pyproject_toml: Path) -> None:
        result = run_uvtask(["help", "test"], pyproject_toml.parent)
        assert result.returncode == 0

    def test_help_unknown_command(self, pyproject_toml: Path) -> None:
        result = run_uvtask(["help", "nonexistent"], pyproject_toml.parent)
        assert result.returncode == 1
        assert "error" in result.stderr.lower() or "unknown" in result.stderr.lower()


class TestMultilineCommands:
    def test_multiline_command_with_description(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_content = '''[tool.run-script]
clean = { command = """python3 -c "
import os
print('Cleaning...')
print('Done!')
"
""", description = "Clean build artifacts" }
'''
        pyproject_path.write_text(pyproject_content)

        result = run_uvtask(["clean"], temp_dir)
        assert result.returncode == 0
        assert "Cleaning..." in result.stdout
        assert "Done!" in result.stdout

    def test_multiline_command_help(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_content = '''[tool.run-script]
clean = { command = """python3 -c "
import os
print('Clean')
"
""", description = "Clean build artifacts" }
'''
        pyproject_path.write_text(pyproject_content)

        result = run_uvtask(["help", "clean"], temp_dir)
        assert result.returncode == 0
        assert "Clean build artifacts" in result.stdout


class TestCommandChaining:
    def test_command_references_other_commands(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_content = '''[tool.run-script]
lint = "echo lint"
test = "echo test"
check = { command = ["lint", "test"], description = "Run lint and test" }
'''
        pyproject_path.write_text(pyproject_content)

        result = run_uvtask(["check"], temp_dir)
        assert result.returncode == 0
        assert "lint" in result.stdout
        assert "test" in result.stdout

    def test_nested_command_references(self, temp_dir: Path) -> None:
        pyproject_path = temp_dir / "pyproject.toml"
        pyproject_content = '''[tool.run-script]
lint = "echo lint"
format = "echo format"
static = { command = ["lint", "format"], description = "Static analysis" }
all = { command = ["static"], description = "Run all checks" }
'''
        pyproject_path.write_text(pyproject_content)

        result = run_uvtask(["all"], temp_dir)
        assert result.returncode == 0
        assert "lint" in result.stdout
        assert "format" in result.stdout


class TestErrorHandling:
    def test_unknown_command(self, pyproject_toml: Path) -> None:
        result = run_uvtask(["unknown"], pyproject_toml.parent)
        assert result.returncode == 1
        assert "error" in result.stderr.lower()

    def test_missing_pyproject(self, temp_dir: Path) -> None:
        result = run_uvtask(["test"], temp_dir)
        assert result.returncode == 1
        assert "pyproject.toml" in result.stderr.lower()
