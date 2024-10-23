"""A script to create rCell files from one syncropatch experiment.

Input and output folders are set in the .env file.

The script can be run with with an experiment name as argument
"""

import os
from pathlib import Path
import argparse

from ..conversion.main import convert_to_nwb


def main():
    args = parse_args()
    exp_name = args.exp_name
    year = "20" + exp_name[:2]
    path_exp = Path(os.getenv("SYNCROPATCH_RAW_DATA_PATH")) / year / exp_name
    print(f"inputs are [{path_exp}] and [{args.overwrite}]")
    convert_to_nwb(path_exp, overwrite=args.overwrite)
    return

def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--overwrite",
        help="Replace existing rCell files",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "exp_name",
        type=str,
    )
    args = parser.parse_args()
    return args
