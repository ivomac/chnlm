"""A script to create rCell files from one igor experiment.

Input and output folders are set in the .env file.
Cell id could be added to store to the proper id (default 0)

The script can be run with with an experiment name as argument
"""

import os
from pathlib import Path
import argparse
import re

from ..conversion.main import convert_to_nwb

RAW_PATH = Path(os.environ["IGOR_RAW_DATA_PATH"])


def main(argin=None):
    args = parse_args(argin)

    paths = [get_full_path(exp_name) for exp_name in args.exp_name]

    # Convert all files if no exp_name is provided
    if not paths:
        paths = list(RAW_PATH.rglob("*.h5xp"))

    failures = 0
    cell_id = args.cell_id
    for path in paths:
        try:
            convert_to_nwb(
                path,
                cell_id=cell_id,
                overwrite=args.overwrite,
                validate=args.validate,
            )
            cell_id += 1
        except Exception as e:
            if not args.allow_failure:
                raise e
            failures += 1
            print(f"Conversion Failure on {path.stem}: {e}")

    if len(paths) > 1:
        ratio = failures / len(paths)
        print(f"Failures: {failures} / {len(paths)} ({ratio:.1%})")
    return


def get_full_path(exp_name):
    year_month = re.findall(r"[a-zA-Z](\d+)_", exp_name)[0][:4]
    year = "Year20" + year_month[:2]
    return RAW_PATH / year / year_month / exp_name


def parse_args(args):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        help="Replace existing rCell files",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--validate",
        help="Validate the rCell dictionary before saving it",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--cell-id",
        help="Cell id of the first rCell to be created",
        type=int,
        default=0,
    )
    parser.add_argument(
        "-a",
        "--allow-failure",
        help="Continue conversion of next experiment on failure",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "exp_name",
        nargs="*",
        type=str,
    )
    return parser.parse_args(args)
