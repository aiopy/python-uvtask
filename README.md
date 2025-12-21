# 🚀 uvtask

[![PyPI version](https://badge.fury.io/py/uvtask.svg)](https://badge.fury.io/py/uvtask)
[![PyPIDownloads](https://static.pepy.tech/badge/uvtask)](https://pepy.tech/project/uvtask)

**uvtask** is a modern, fast, and flexible Python task runner and test automation tool designed to simplify development workflows. It supports running, organizing, and managing tasks or tests in Python projects with an emphasis on ease of use and speed. ⚡

## 📦 Installation

```bash
uv add --dev uvtask
```

## 🎯 Quick Start

Run tasks defined in your `pyproject.toml`:

```shell
uvx uvtask run <task_name>
```

## 📝 Configuration

Define your tasks in `pyproject.toml` under the `[tool.run-script]` section:

```toml
[tool.run-script]
code-formatter = "uv run ruff format uvtask tests $@"
"security-analysis:licenses" = "uv run pip-licenses"
"security-analysis:vulnerabilities" = "uv run bandit -r -c pyproject.toml uvtask tests"
"static-analysis:linter" = "uv run ruff check uvtask tests"
"static-analysis:types" = "uv run ty check uvtask tests"
test = "uv run pytest"
unit-tests = "uv run pytest tests/unit"
integration-tests = "uv run pytest tests/integration"
functional-tests = "uv run pytest -n1 tests/functional"
```

## 🛠️ Development

To run the development version:

```shell
uvx --no-cache --from $PWD run --help
```

## 📋 Requirements

- 🐍 Python >= 3.13

## 🤝 Contributing

Contributions are welcome! 🎉

- For major changes, please open an issue first to discuss what you would like to change
- Make sure to update tests as appropriate
- Follow the existing code style and conventions

## 📄 License

[MIT](https://github.com/aiopy/python-uvtask/blob/master/LICENSE) © uvtask contributors
