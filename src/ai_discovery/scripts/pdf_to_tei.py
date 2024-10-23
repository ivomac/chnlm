"""
From a list of pubmed_id in paper/pubmed_ids.txt and the already downloaded xml for pubmed central,
download the free pdf online got from https://unpaywall.org/products/api, and download to ../paper/pdf.

Features:
1- Possible overwrite parameter:
    - if False: will only download xml not already in paper/xml
"""
import os
from pathlib import Path
import asyncio
import argparse
from ..database.tei import bash_extract
from ..database.query import QUERY
from ..database.utils import get_tei_path, get_pdf_path

def main(argin=None):
    args = parse_args(argin)
    index_name = args.index_name
    asyncio.run(
        bash_extract(
            pdf_path = get_pdf_path(index_name),
            tei_path = get_tei_path(index_name),
            backup_path = get_tei_path("backup"),
            overwrite=False,
            grobid_url='http://ml-bbs-grobid.kcp.bbp.epfl.ch',
            sample=False,
            window=1,
            nb_concurrent=1
        )
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
    parser.add_argument(
        "--overwrite",
        help="Replace existing pmc xml",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--sample",
        help="Download only the first 100",
        default=False,
        action="store_true",
    )

    return parser.parse_args(args)