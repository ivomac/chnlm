from .main import convert_to_nwb
from ..utils import SEPARATOR
from dagster import ( asset, AssetExecutionContext,
    Output, Config, define_asset_job, DynamicPartitionsDefinition)
from pathlib import Path
from typing import List
from pydantic import Field
import os

class FileConfig(Config):
    filepath: str = Field(description='filepath of the raw data', is_required=True)
    cell_ids: List[int] = Field(description='Allocated cell ids', is_required=True)

patchliner_partitions_def = DynamicPartitionsDefinition(name="patchliner")

@asset(partitions_def=patchliner_partitions_def)
def patchliner_to_nwb(context: AssetExecutionContext):
    raw_RAW_DATA_PATH = Path(os.getenv('RAW_DATA_PATH'))
    
    year, exp_name = context.partition_key.split(SEPARATOR)
    
    filepath = raw_RAW_DATA_PATH / year / "patchliner" / (exp_name + ".dat")
    cell_ids=""
    # recollect cell_ids 
    for cell_id, nwb_filepath, nwb_file in convert_to_nwb(filepath, cell_ids):
        nwb_filepath.unlink(missing_ok=True)
        nwb_file.model_dump_h5(nwb_filepath, close_handle=True)
    
    context.add_output_metadata({"experiment": filepath.stem, "saving_folder": str(exp_name), "nb_cells": len(cell_ids), "allocated_cell_ids": cell_ids, "drug": "retigabine", "channel": "Kv1.1"})    
    yield Output(cell_ids, output_name="result")

extract_patchliner_to_nwb = define_asset_job(name="extract_patchliner_to_nwb", selection=["patchliner_to_nwb"])