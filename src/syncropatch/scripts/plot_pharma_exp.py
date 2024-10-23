"""A script to pharma plot response from one syncropatch experiment.

Input and output folders are set in the .env file.

The script can be run with with an experiment name as argument
"""

import os
from pathlib import Path
import argparse

def plot_pharma_experiment(path):


def main():
    args = parse_args()
    exp_name = args.exp_name
    year = exp_name.split('_')[0]
    path_exp = Path(os.getenv("SYNCROPATCH_NWB_PATH")) / year / exp_name
    plot_pharma_experiment(path_exp, overwrite=args.overwrite)
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
