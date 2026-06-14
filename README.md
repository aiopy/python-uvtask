# uvtask

[![image](https://img.shields.io/pypi/v/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![image](https://img.shields.io/pypi/l/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![image](https://img.shields.io/pypi/pyversions/uvtask.svg)](https://pypi.python.org/pypi/uvtask)
[![Actions status](https://github.com/aiopy/python-uvtask/actions/workflows/ci.yml/badge.svg)](https://github.com/aiopy/python-uvtask/actions)
[![PyPIDownloads](https://static.pepy.tech/badge/uvtask)](https://pepy.tech/project/uvtask)

A task runner for `pyproject.toml` scripts, optimized for the uv workflow.

Define commands once in TOML, run them with `uvx uvtask` from any machine — zero runtime dependencies in your project.

## Why uvtask

- **Run anywhere with `uvx`** — no install required; zero runtime dependencies
- **Scripts live in `pyproject.toml`** — under `[tool.run-script]` or `[tool.uvtask.run-script]`
- **Compose pipelines without shell glue** — chain commands by referencing other script names
- **Pre/post hooks** — Composer-style (`pre-test` / `post-test`) or NPM-style (`pretest` / `posttest`)
- **uv-like CLI** — colored output, structured help, and typo suggestions for unknown commands
- **Forward arguments safely** — extra CLI args pass through to the underlying command, including JSON and values with spaces

Pick uvtask when you want npm/composer-style project scripts in Python, with a CLI that feels at home next to `uv`, `ruff`, and `ty`.

## Quick Start

**1. Add scripts to `pyproject.toml`:**

```toml
[tool.run-script]
lint = "uv run ruff check ."
test = "uv run pytest"
check = ["lint", "test"]
```

**2. Run them:**

```shell
uvx uvtask check
uvx uvtask test -k integration   # args forwarded to pytest
```

For daily use, install once with `uv tool install uvtask`, then run `uvtask` directly.

## Features

### Configuration formats

Scripts support several TOML shapes:

```toml
[tool.run-script]
# Simple string
format = "uv run ruff format ."

# With description (shown in help)
lint = { command = "uv run ruff check .", description = "Check code quality" }

# Multiple commands run in sequence
check = ["lint", "test"]

# Multiline commands
deploy = """
echo 'Building...'
uv build
echo 'Done!'
"""
```

You can also nest scripts under `[tool.uvtask.run-script]` if you prefer a namespaced layout.

See this repository's [pyproject.toml](pyproject.toml) for a full real-world script catalog.

### Command composition

Reference other script names to build pipelines without repeating shell commands:

```toml
[tool.run-script]
lint = "uv run ruff check ."
test = "uv run pytest"
static = ["lint", "test"]
all = ["static"]
```

Running `uvx uvtask all` executes `lint` then `test`.

### Hooks

Define hooks that run automatically before and after a command:

```toml
[tool.run-script]
pre-test = "echo 'Setting up...'"
test = "uv run pytest"
post-test = "echo 'Cleaning up...'"
```

Both naming styles are supported:

| Style    | Pre-hook   | Post-hook   |
|----------|------------|-------------|
| Composer | `pre-test` | `post-test` |
| NPM      | `pretest`  | `posttest`  |

Skip hooks when needed:

```shell
uvx uvtask --no-hooks test
```

### Arguments

Extra arguments after the command name are forwarded to the underlying script:

```shell
uvx uvtask test -k integration -x
uvx uvtask celery-call example -k '{"kwarg": "value"}'
```

Values with spaces and JSON are quoted correctly for the shell on both Unix and Windows.

### Namespaced commands

Use colons to group related commands:

```toml
[tool.run-script]
static-analysis = { command = ["static-analysis:linter", "static-analysis:types"], description = "Run all static analysis checks" }
"static-analysis:linter" = "uv run ruff check ."
"static-analysis:types" = "uv run ty check ."
```

## CLI reference

| Flag | Purpose |
|------|---------|
| `-q` / `--quiet` | Suppress stdout (stackable) |
| `-v` / `--verbose` | Show command and exit codes (stackable) |
| `--no-hooks` / `--ignore-scripts` | Skip pre/post hooks |
| `--color` | Control color output: `auto`, `always`, or `never` |
| `help [command]` | Show per-command documentation from `description` |
| `-V` / `--version` | Print version |
| `-h` / `--help` | Print general help |

## Comparison

| Tool | Best for | uvtask difference |
|------|----------|-------------------|
| `uv run` / `uvx` | One-off tool invocations | Named, documented project commands with hooks and composition |
| [Poe the Poet](https://github.com/nat-n/poethepoet) | Rich task runner with templating | Zero deps, `uvx`-native, uv-styled CLI |
| [Hatch scripts](https://hatch.pypa.io/) | Hatch-managed projects | Tool-agnostic `pyproject.toml` config, works with any uv project |
| npm / Composer scripts | JS / PHP ecosystems | Same mental model, Python-native |

## Development

Run the development version from a local checkout:

```shell
uvx -q --no-cache --from $PWD uvtask
```

Common project tasks:

```shell
uvx uvtask static-analysis
uvx uvtask test
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT](https://github.com/aiopy/python-uvtask/blob/master/LICENSE) © uvtask contributors

---

**Note:** uvtask is an independent, third-party project — not an official Astral tool. It is inspired by and designed to work seamlessly with Astral's excellent tools (`uv`, `ruff`, `ty`). We're grateful for the work the Astral team does for the Python ecosystem.
