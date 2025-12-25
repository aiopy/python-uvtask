from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def pyproject_toml(temp_dir: Path) -> Path:
    pyproject_path = temp_dir / "pyproject.toml"
    pyproject_content = """[tool.run-script]
test = "echo test"
build = "echo build"
lint = "echo lint"
"multi-word" = "echo multi"
"""
    pyproject_path.write_text(pyproject_content)
    return pyproject_path


@pytest.fixture
def empty_pyproject_toml(temp_dir: Path) -> Path:
    pyproject_path = temp_dir / "pyproject.toml"
    pyproject_content = """[project]
name = "test"
version = "0.2.0"
"""
    pyproject_path.write_text(pyproject_content)
    return pyproject_path
