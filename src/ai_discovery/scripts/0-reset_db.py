
"""
Reset db
"""
from pathlib import Path
import os
import argparse
from ..database.dbsearch import get_dbsearch
from ..database.query import QUERY


def main(argin=None):
    args = parse_args(argin)
    index_name = args.index_name
    document_store, mappings, settings = get_dbsearch(
        db_url=os.getenv('ES_HOST'),
        user=os.getenv('ES_USERNAME', None),
        password=os.getenv('ES_PASSWORD', None)
    )
    settings["number_of_shards"] = 1
    try:
        document_store.remove_index(index_name)
        print(f"index {index_name} removed")
    except:
        pass
    document_store.create_index(index_name, settings, mappings)
    print(f"index {index_name} created")


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