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
from ..search.chain import run_one_channel_drug
from ..search.channels_drugs import CHANNELS, DRUGS



async def main(argin=None):
    args = parse_args(argin)

    await run_one_channel_drug(args.channel_name, args.drug_name, args.overwrite)




def parse_args(args):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--channel_name",
        type=str,
        default='Nav1.7',
        choices=list(CHANNELS.keys())
    )
    parser.add_argument(
        "--drug_name",
        type=str,
        default='Retigabine',
        choices=list(DRUGS.keys())
    )
    parser.add_argument(
        "--overwrite",
        help="Replace existing pmc xml",
        default=False,
        action="store_true",
    )

    return parser.parse_args(args)