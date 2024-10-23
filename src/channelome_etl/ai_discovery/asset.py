
from dagster import asset, AssetExecutionContext, graph_asset, op, StaticPartitionsDefinition, define_asset_job, OpExecutionContext, In, Nothing, MultiPartitionsDefinition
from pathlib import Path
from typing import List
from ai_discovery.database.pmc import fetch_pubmed_ids, bash_download as pmc_bash_download
from ai_discovery.database.abstract import bash_download as abstract_bash_download
from ai_discovery.database.pdf import bash_download as pdf_bash_download
from ai_discovery.database.tei import bash_extract as tei_bash_download
from dagster_shell import create_shell_command_op, execute_shell_command, shell_op
import os
import re
import asyncio
import logging
from scholarag.scripts import manage_index
from ai_discovery.database.dbsearch import get_dbsearch, run as fill_db
from ai_discovery.database.utils import get_pubmed_ids_path, get_xml_path, get_abstract_path, get_pdf_path, get_tei_path
from ai_discovery.database.query import QUERY


ai_db_partitions_def = StaticPartitionsDefinition(
    list(QUERY.keys())
)

# --------------- Open access paper that can only be found in open access mode on internet ---------------------------------

@asset(partitions_def=ai_db_partitions_def)
def reset_db(context: AssetExecutionContext):
    index_name = context.partition_key
    document_store, mappings, settings = get_dbsearch(
        db_url=os.getenv('ES_HOST'),
        user=os.getenv('ES_USERNAME', None),
        password=os.getenv('ES_PASSWORD', None)
    )
    try:
        document_store.remove_index(index_name)
        print(f"index {index_name} removed")
    except:
        pass
    settings["number_of_shards"] = 1
    document_store.create_index(index_name, settings, mappings)
    print(f"index {index_name} created")

@asset(partitions_def=ai_db_partitions_def, deps=[reset_db])
def get_pubmed_ids(context: AssetExecutionContext):
    overwrite = False
    index_name = context.partition_key
    pubmed_ids_path = get_pubmed_ids_path(index_name)
    query = QUERY[index_name]
    if query is None:
        return ""
    
    if pubmed_ids_path.exists():
        if not overwrite:
            return ""
        pubmed_ids_path.unlink()
    else:
        pubmed_ids_path.parent.mkdir(parents=True, exist_ok=True)
    
    output, return_code = execute_shell_command(f"esearch -db pubmed -query '{query}' | efetch -format uid >> {pubmed_ids_path.resolve()}", output_logging="STREAM", log=context.log)
    if return_code != 0:
        raise Exception(f"Shell script failed with return code {return_code}")
    return ""

@asset(partitions_def=ai_db_partitions_def, deps=[get_pubmed_ids])
def pmc(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access xml from pubmed central database"""
    asyncio.run(
        pmc_bash_download(
            pubmed_ids_path=get_pubmed_ids_path(index_name),
            XML_path=get_xml_path(index_name),
            backup_path=get_xml_path("backup"),
            use_backup=True,
            overwrite=False,
            sample=False
        )
    )

@asset(partitions_def=ai_db_partitions_def, deps=[pmc])
def fill_pmc(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access xml from pubmed central database"""
    asyncio.run(
        fill_db(
            path=get_xml_path(index_name),
            failed_path=get_xml_path(index_name, failed=True),
            parser_url= "https://ml-bbs-etl.kcp.bbp.epfl.ch/jats_xml",
            db_url= os.getenv('ES_HOST'),
            multipart_params= None,
            max_concurrent_requests= 10,
            articles_per_bulk= 100,
            index= index_name,
            db_type= "elasticsearch",
            max_length = 200,
            min_length = 10,
            use_ssl = False,
        )
    )

@asset(partitions_def=ai_db_partitions_def, deps=[fill_pmc])
def abstract(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access abstrect from pubmed database or google scholar"""
    asyncio.run(
        abstract_bash_download(
            pubmed_ids_path=get_pubmed_ids_path(index_name),
            XML_path=get_xml_path(index_name),
            abstract_path=get_abstract_path(index_name),
            backup_path=get_abstract_path("backup"),
            use_backup=True,
            overwrite=False,
            sample=False
        )
    )

@asset(partitions_def=ai_db_partitions_def, deps=[abstract])
def fill_abstract(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access xml from pubmed central database"""
    asyncio.run(
        fill_db(
            path=get_abstract_path(index_name),
            failed_path=get_abstract_path(index_name, failed=True),
            parser_url= "https://ml-bbs-etl.kcp.bbp.epfl.ch/pubmed_xml",
            db_url= os.getenv('ES_HOST'),
            multipart_params= None,
            max_concurrent_requests= 10,
            articles_per_bulk= 100,
            index= index_name,
            db_type= "elasticsearch",
            max_length = 200,
            min_length = 10,
            use_ssl = False,
        )
    )

@asset(partitions_def=ai_db_partitions_def, deps=[fill_abstract])
def pdf(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access pdf form anywhrere"""
    asyncio.run(
        pdf_bash_download(
            pubmed_ids_path=get_pubmed_ids_path(index_name),
            XML_path=get_xml_path(index_name),
            pdf_path=get_pdf_path(index_name),
            backup_path=get_pdf_path("backup"),
            use_backup=True if index_name=="close_access" else False,
            overwrite=False,
            sample=False
            )
        )

@asset(partitions_def=ai_db_partitions_def, deps=[pdf])
def tei(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access pdf form anywhrere"""
    asyncio.run(
        tei_bash_download(
            pdf_path = get_pdf_path(index_name),
            tei_path = get_tei_path(index_name),
            backup_path = get_tei_path("backup"),
            use_backup=True,
            overwrite=False,
            grobid_url = 'http://ml-bbs-grobid.kcp.bbp.epfl.ch',
            sample=False,
            window=100,
            nb_concurrent=1
            )
        )

@asset(partitions_def=ai_db_partitions_def, deps=[tei])
def fill_tei(context: AssetExecutionContext):
    index_name = context.partition_key
    """Fetch all Open Access xml from pubmed central database"""
    asyncio.run(
        fill_db(
            path=get_tei_path(index_name),
            failed_path=get_tei_path(index_name, failed=True),
            parser_url= "https://ml-bbs-etl.kcp.bbp.epfl.ch/tei_xml",
            db_url= os.getenv('ES_HOST'),
            multipart_params= None,
            max_concurrent_requests= 10,
            articles_per_bulk= 100,
            index= index_name,
            db_type= "elasticsearch",
            max_length = 200,
            min_length = 10,
            use_ssl = False,
        )
    )

extract_and_fill_documents = define_asset_job(
    name="extract_and_fill_documents",
    selection=
        [   
            "reset_db",
            "get_pubmed_ids",
            "pmc",
            "fill_pmc",
            "abstract",
            "fill_abstract",
            "pdf",
            "tei",
            "fill_tei"
        ]
    )

# ----------------------------Drug Screening---------------------------------------------------

from ai_discovery.search.channels_drugs import CHANNELS, DRUGS
from ai_discovery.search.chain import run_one_channel_drug
from ai_discovery.search.sql import remove_main_table

drug_screening_partitions_def = MultiPartitionsDefinition(
    {   
        "drug": StaticPartitionsDefinition(list(DRUGS.keys())),
        "channel": StaticPartitionsDefinition(list(CHANNELS.keys()))
        
    }
)

@asset()
def remove_drug_sreening_table(context: AssetExecutionContext):
    remove_main_table()

@asset(partitions_def=drug_screening_partitions_def)
def drug_screening(context: AssetExecutionContext):
    partitions = context.partition_key.keys_by_dimension
    """Fetch all Open Access xml from pubmed central database"""
    return asyncio.run(
        run_one_channel_drug(
            partitions["channel"],
            partitions["drug"],
            overwrite=False
        )
    )

