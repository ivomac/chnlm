from .qpc.sensor import qpc_raw_data_file_sensor
from .qpc.asset import extract_qpc_to_nwb, qpc_to_nwb

from .syncropatch.sensor import syncropatch_raw_data_file_sensor
from .syncropatch.asset import (
    extract_syncropatch_to_nwb,
    syncropatch_plots,
    syncropatch_to_nwb,
    syncropatch_acell,
    syncropatch_to_csv,
)

from .igor.sensor import igor_raw_data_file_sensor
from .igor.asset import igor_to_nwb, extract_igor_to_nwb

from .ai_discovery.asset import (reset_db, get_pubmed_ids, pmc, fill_pmc,
                                 abstract, fill_abstract, pdf, tei, fill_tei,
                                 extract_and_fill_documents,
                                 drug_screening, remove_drug_sreening_table)

from .notification.sensor import job_run_failure, conversion_job_success

from dagster_slack import SlackResource
from dagster import Definitions
from dotenv import load_dotenv
import os

load_dotenv()


defs = Definitions(
    assets=[
        syncropatch_to_nwb,
        syncropatch_acell,
        syncropatch_to_csv,
        syncropatch_plots,
        qpc_to_nwb, 
        igor_to_nwb,
        reset_db, get_pubmed_ids, pmc, fill_pmc,
        abstract, fill_abstract, pdf, tei, fill_tei,
        drug_screening, remove_drug_sreening_table
    ],
    jobs=[
        extract_syncropatch_to_nwb,
        extract_qpc_to_nwb,
        extract_igor_to_nwb,
        extract_and_fill_documents
    ],
    sensors=[
        syncropatch_raw_data_file_sensor,
        qpc_raw_data_file_sensor,
        igor_raw_data_file_sensor,
        job_run_failure,
        conversion_job_success,
    ],
    resources={
        "slack": SlackResource(token=os.getenv("SLACK_TOKEN")),
    },
)
