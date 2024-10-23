from .asset import extract_igor_to_nwb, igor_partitions_def
from channelome_etl.utils import listdir_nohidden
from pathlib import Path
from dagster import sensor, SensorEvaluationContext, DefaultSensorStatus, RunRequest, SensorResult
import os

@sensor(job=extract_igor_to_nwb, default_status=DefaultSensorStatus.STOPPED, minimum_interval_seconds=600)
def igor_raw_data_file_sensor(context: SensorEvaluationContext):
    #--------------igor----------------------
    next_cell = len(igor_partitions_def.get_partition_keys(dynamic_partitions_store=context.instance))

    igor_raw_data_path = Path(os.getenv('IGOR_RAW_DATA_PATH'))
    context.log.info(igor_raw_data_path)
    partition_keys = []

    if igor_raw_data_path.exists():
        for year in sorted(list(listdir_nohidden(igor_raw_data_path)), key=lambda m: m.name):
            for month in sorted(list(listdir_nohidden(year)), key=lambda m: int(m.name)):
                context.log.info(list(month.glob(".h5xp")))
                for exp_filepath in sorted(list(month.glob("*.h5xp")), key=lambda m: m.stem):
                    exp_name = exp_filepath.stem
                    if exp_filepath.exists() and not (exp_name in igor_partitions_def.get_partition_keys(dynamic_partitions_store=context.instance)):
                        #last_cell_id = last_cell_id + nb_cell
                        partition_keys.append(exp_name)
        return SensorResult(
            run_requests=[RunRequest(
                partition_key=partition_key
            ) for partition_key in partition_keys],
            dynamic_partitions_requests=[
                    igor_partitions_def.build_add_request(partition_keys)
                ],
            )
