"""
Fill PMC in db
"""
from pathlib import Path
import os
import argparse
from ..database.dbsearch import run
from ..database.query import QUERY
from ..database.utils import get_path
import asyncio
import logging

logger = logging.getLogger("parse_and_upload")
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

def main(argin=None):
    args = parse_args(argin)
    index_name = args.index_name
    parser_type = "jats_xml"
    if args.type == "abstract":
        parser_type = "pubmed_xml"
    if args.type == "pdf":
        parser_type = "grobid_pdf"
    if args.type == "tei":
        parser_type = "tei_xml"
    print(get_path(index_name, document_type=args.type, failed=False))
    asyncio.run(
        run(
            path= get_path(index_name, document_type=args.type, failed=False),
            failed_path= get_path(index_name, document_type=args.type, failed=True),
            parser_url= f"https://ml-bbs-etl.kcp.bbp.epfl.ch/{parser_type}",
            db_url= os.getenv('ES_HOST'),
            multipart_params= {} if parser_type in ["grobid_pdf", "tei_xml"] else None,
            max_concurrent_requests= 1,
            articles_per_bulk= 10,
            index= args.index_name,
            db_type= "elasticsearch",
            max_length = 200,
            min_length = 10,
            use_ssl = False,
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
        "--type",
        type=str,
        default='xml',
        choices=["xml", "abstract", "pdf", "tei"]
    )
    return parser.parse_args(args)