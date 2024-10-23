"""A script to create rCell files from one syncropatch experiment.

Input and output folders are set in the .env file.

The script can be run with with an experiment name as argument
"""

import os
from pathlib import Path
import argparse

from ..analysis.acell import AcellSaver


def main():
    args = parse_args()
    cell_id = args.cell_id
    dateStr, expName, c_id, _ = cell_id.split('_')
    rcell_path = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / "rcell" / dateStr / '_'.join([dateStr, expName]) / '_'.join([dateStr, expName, c_id]) / (cell_id + '.nwb')
    print(f"rcell path is [{rcell_path}] and [{args.overwrite}]")
    acell = AcellSaver(rcell_path=rcell_path)
    acell.save(args.overwrite)
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
        "cell_id",
        type=str,
    )
    args = parser.parse_args()
    return args
