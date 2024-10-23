"""
Fetch all pubmed ids from a query in a txt file
"""
from pathlib import Path
import os
import argparse
from ..database.pmc import fetch_pubmed_ids 
from ..database.query import QUERY
from ..database.utils import get_pubmed_ids_path


def main(argin=None):
    args = parse_args(argin)
    index_name = args.index_name
    fetch_pubmed_ids(
        query=QUERY[index_name],
        saving_path=get_pubmed_ids_path(index_name=index_name)
    )


def parse_args(args):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "index_name",
        type=str,
        default='close_access',
        choices=list(QUERY.keys())
    )
    return parser.parse_args(args)