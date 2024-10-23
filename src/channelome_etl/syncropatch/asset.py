from syncropatch.conversion.main import convert_to_nwb
from syncropatch.analysis.acell import AcellSaver, csv_from_acells
from syncropatch.plot.main import plot_experiment
from dagster import ( asset, AssetExecutionContext,
    Output, Config, define_asset_job, DynamicPartitionsDefinition)
from pathlib import Path
from typing import List
from pydantic import Field
import os

class FileConfig(Config):
    filepath: str = Field(description='filepath of the raw data', is_required=True)
    cell_ids: List[int] = Field(description='Allocated cell ids', is_required=True)

syncropatch_partitions_def = DynamicPartitionsDefinition(name="syncropatch")

@asset(partitions_def=syncropatch_partitions_def)
def syncropatch_to_nwb(context: AssetExecutionContext):
    """Create rCells for Syncropatch experiments.
    """
    SYNCROPATCH_RAW_DATA_PATH = Path(os.getenv('SYNCROPATCH_RAW_DATA_PATH'))
    exp_folder = context.partition_key
    year = "20" + exp_folder[:2]
    filepath = SYNCROPATCH_RAW_DATA_PATH / year / exp_folder
    convert_to_nwb(filepath)
    context.add_output_metadata({"experiment": filepath.stem, "saving_folder": str(context.partition_key), "drug": "retigabine", "channel": "Kv1.1"})    
    yield Output("", output_name="result")

@asset(deps=[syncropatch_to_nwb], partitions_def=syncropatch_partitions_def)
def syncropatch_plots(context: AssetExecutionContext):
    """Basic plot of rCells for Syncropatch experiments.
    """
    SYNCROPATCH_NWB_PATH = Path(os.getenv('SYNCROPATCH_NWB_PATH'))
    exp_folder = context.partition_key
    # Rajnish want a different config 
    filepath = SYNCROPATCH_NWB_PATH / "rcell" / exp_folder.split('_')[0] / exp_folder
    plot_experiment(filepath)
    context.add_output_metadata({"experiment": filepath.stem, "saving_folder": str(context.partition_key), "drug": "retigabine", "channel": "Kv1.1"})    
    yield Output("", output_name="result")

@asset(deps=[syncropatch_to_nwb], partitions_def=syncropatch_partitions_def)
def syncropatch_acell(context: AssetExecutionContext):
    """Basic plot of rCells for Syncropatch experiments.
    """
    SYNCROPATCH_NWB_PATH = Path(os.getenv('SYNCROPATCH_NWB_PATH'))
    exp_folder = context.partition_key
    # Rajnish want a different config 
    rcell_filepath = SYNCROPATCH_NWB_PATH / "rcell" / exp_folder.split('_')[0] / exp_folder

    for rcell_filepath in rcell_filepath.glob('**/*.nwb'):
        acell = AcellSaver(rcell_filepath)
        acell.save(overwrite=True)
    context.add_output_metadata({"experiment": rcell_filepath.stem, "saving_folder": str(context.partition_key), "drug": "retigabine", "channel": "Kv1.1"})    
    yield Output("", output_name="result")

@asset
def syncropatch_to_csv(context: AssetExecutionContext):
    """Basic plot of rCells for Syncropatch experiments.
    """
    csv_from_acells(saving_path=Path(os.getenv('SYNCROPATCH_NWB_PATH')))
    yield Output("", output_name="result")


extract_syncropatch_to_nwb = define_asset_job(name="extract_syncropatch_to_nwb", selection=["syncropatch_to_nwb", "syncropatch_plots", "syncropatch_acell"])
