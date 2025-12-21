from pathlib import Path
from subprocess import run
from sys import argv, exit
from tomllib import loads


def main() -> None:
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found in current directory!")
        exit(1)

    with open(pyproject_path) as file:
        scripts = loads(file.read()).get("tool", {}).get("run-script", {})

    args = argv[1:]

    if len(args) == 0:
        args.append("-h")

    if args[0] == "-h" or args[0] == "-help" or args[0] == "--help":
        commands = (chr(10) + "  ").join(scripts.keys())
        print("Usage: uvtask [COMMAND]\n\nCommands:\n  {0}\n\nOptions:\n  -h,--help".format(commands))
        exit(0)

    script = scripts.get(args[0])
    if not script:
        print(f"Error: Unknown command '{args[0]}'!")
        print("Run 'uvtask --help' to see available commands.")
        exit(1)

    script_args = " ".join(args[1:]) if len(args) > 1 else ""
    command = f"{script} {script_args}".strip()

    try:
        exit(run(command, check=False, shell=True).returncode)
    except KeyboardInterrupt:
        exit(130)
