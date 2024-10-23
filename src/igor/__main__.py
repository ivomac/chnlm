"""A python module to convert Igor data to H5/NWB formats.
Provides a command line interface to run scripts.
Run each script with the -h flag to see the available options.
"""

import argparse
import importlib
from pathlib import Path

SCRIPT_FOLDER = Path(__file__).parent / "scripts"

SCRIPT_FILES = [
    script for script in SCRIPT_FOLDER.glob("*.py") if not script.stem.startswith("_")
]

SCRIPTS = [script.stem for script in SCRIPT_FILES]


def main():
    cmd, args = parse_args()
    script = importlib.import_module(f".scripts.{cmd.name}", package="igor")
    script.main(args)
    return


def parse_args():
    parser = argparse.ArgumentParser(
        description=generate_description(),
        add_help=False,
        prog="python -m /path/to/igor",
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
