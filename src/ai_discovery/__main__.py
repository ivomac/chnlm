"""A python module to ai in channelome project, namely channelaid and AI drug screening
"""

import argparse
import importlib
from pathlib import Path
import asyncio

SCRIPT_FOLDER = Path(__file__).parent / "scripts"

SCRIPT_FILES = [
    script for script in SCRIPT_FOLDER.glob("*.py") if not script.stem.startswith("_")
]

SCRIPTS = [script.stem for script in SCRIPT_FILES]


def main():
    cmd, args = parse_args()
    script = importlib.import_module(f".scripts.{cmd.name}", package="ai_discovery")
    if asyncio.iscoroutinefunction(script.main):
        asyncio.run(script.main(args))
    else:
        script.main(args)
    return


def parse_args():
    parser = argparse.ArgumentParser(
        description=generate_description(),
        add_help=False,
        prog="python -m /path/to/ai_discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("name", choices=SCRIPTS, metavar="<script>", nargs="?")

    cmd, args = parser.parse_known_args()
    if cmd.name is None:
        parser.print_help()
        exit()
    return cmd, args


def generate_description():
    script_descs = [script_description(script) for script in SCRIPT_FILES]
    opts = "\n".join(script_descs)
    desc = f"{__doc__}\nAvailable scripts:\n{opts}"
    return desc


def script_description(script):
    with script.open() as f:
        line = f.readline()
    line = line.strip("\"'# \n\t")
    return f"  {script.stem}: {line}"


if __name__ == "__main__":
    main()
