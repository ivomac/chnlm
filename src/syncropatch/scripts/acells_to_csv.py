"""A script to create rCell files from one syncropatch experiment.

Input and output folders are set in the .env file.

The script can be run with with an experiment name as argument
"""

import os
from pathlib import Path
import argparse

from ..analysis.acell import csv_from_acells


def main():
    args = parse_args()
    csv_from_acells(saving_path=Path(os.getenv('SYNCROPATCH_NWB_PATH')))
    return

def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    args = parser.parse_args()
    return args
