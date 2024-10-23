from .asset import extract_syncropatch_to_nwb, syncropatch_partitions_def
from ..utils import listdir_nohidden
from dagster import (
    sensor, RunRequest, DefaultSensorStatus, SensorEvaluationContext, SensorResult)
from pathlib import Path
from typing import List
from pydantic import Field
import os
import time


@sensor(job=extract_syncropatch_to_nwb, default_status=DefaultSensorStatus.STOPPED, minimum_interval_seconds=600)
def syncropatch_raw_data_file_sensor(context: SensorEvaluationContext):
    #--------------syncropatch----------------------
    syncropatch_raw_data_path = Path(os.getenv('SYNCROPATCH_RAW_DATA_PATH'))
    partition_keys = []
    if syncropatch_raw_data_path.exists():
        for year in listdir_nohidden(Path(syncropatch_raw_data_path)):
            for exp_filepath in listdir_nohidden(Path(year)):
                exp_folder = exp_filepath.name
                if not syncropatch_partitions_def.has_partition_key(exp_folder, dynamic_partitions_store=context.instance) and exp_filepath.exists():
                    #last_cell_id = last_cell_id + nb_cell
                    partition_keys.append(exp_folder)
        return SensorResult(
            run_requests=[RunRequest(
                partition_key=partition_key
            ) for partition_key in partition_keys],
            dynamic_partitions_requests=[
                    syncropatch_partitions_def.build_add_request(partition_keys)
                ],
            )
