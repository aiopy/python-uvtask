# uvtask

[![image](https://img.shields.io/pypi/v/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![image](https://img.shields.io/pypi/l/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![image](https://img.shields.io/pypi/pyversions/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![Actions status](https://github.com/aiopy/python-uvtask/actions/workflows/ci.yml/badge.svg)](https://github.com/aiopy/python-uvtask/actions)
[![PyPIDownloads](https://static.pepy.tech/badge/uvtask)](https://pepy.tech/project/uvtask)

An extremely fast Python task runner.

## Highlights

- ⚡ **Extremely fast** - Built for speed with zero installation overhead
- 📝 **Simple configuration** - Define scripts in `pyproject.toml`
- 🔗 **Pre/post hooks** - Automatically run hooks before and after commands
- 🎨 **Beautiful output** - Colorful, `uv`-inspired CLI

## 🎯 Quick Start

Run `uvtask` directly with `uvx` (no installation required):

```shell
uvx uvtask <OPTIONS> [COMMAND]
```

Or install it and use it directly:

```shell
uv add --dev uvtask
uvtask <OPTIONS> [COMMAND]
```

## 📝 Configuration

Define your scripts in `pyproject.toml` under the `[tool.run-script]` (or `[tool.uvtask.run-script]`) section:

```toml
[tool.run-script]
install = "uv sync --dev --all-extras"
format = "uv run ruff format ."
lint = { command = "uv run ruff check .", description = "Check code quality" }
check = ["uv run ty check .", "uv run mypy ."]
pre-test = "echo 'Running tests...'"
test = "uv run pytest"
post-test = "echo 'Tests completed!'"
deploy = [
    "echo 'Building...'",
    "uv build",
    "echo 'Deploying...'",
    "uv deploy"
]
```

## 🛠️ Development

To run the development version:

```shell
uvx -q --no-cache --from $PWD uvtask
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[MIT](https://github.com/aiopy/python-uvtask/blob/master/LICENSE) © uvtask contributors
