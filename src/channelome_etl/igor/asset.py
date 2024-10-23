
from dagster import (asset, AssetExecutionContext,
    Output, Config, define_asset_job, DynamicPartitionsDefinition)
from pathlib import Path
from typing import List
from pydantic import Field
from igor.conversion.main import convert_to_nwb
import os
import re

class FileConfig(Config):
    filepath: str = Field(description='filepath of the raw data', is_required=True)
    cell_ids: List[int] = Field(description='Allocated cell ids', is_required=True)

igor_partitions_def = DynamicPartitionsDefinition(name="igor")

@asset(partitions_def=igor_partitions_def)
def igor_to_nwb(context: AssetExecutionContext):
    """Create rCells for Igor experiments."""

    igor_raw_data_path = Path(os.getenv('IGOR_RAW_DATA_PATH'))
    exp_name = context.partition_key
    cell_id = igor_partitions_def.get_partition_keys(dynamic_partitions_store=context.instance).index(exp_name)

    year_month = re.findall(r"[a-zA-Z](\d+)_", exp_name)[0][:4]
    year = "Year20" + year_month[:2]
    cell_id = int(cell_id)
    filepath = igor_raw_data_path / year / year_month / (exp_name + ".h5xp")

    convert_to_nwb(filepath, cell_id=cell_id)
    context.add_output_metadata({"experiment": filepath.stem, "saving_folder": str(exp_name), "allocated_cell_id": cell_id})
    yield Output(cell_id, output_name="result")

extract_igor_to_nwb = define_asset_job(name="extract_igor_to_nwb", selection=["igor_to_nwb"])
