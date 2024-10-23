from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    sensor,
)

from .asset import extract_qpc_to_nwb, qpc_partitions_def
from qpc.conversion.config import CONFIG
from qpc.conversion.google_sheet import GOOGLE_SHEET as GS


def job_id_is_new(job_id: int, context: SensorEvaluationContext) -> bool:
    return not qpc_partitions_def.has_partition_key(
        str(job_id), dynamic_partitions_store=context.instance
    )


@sensor(
    job=extract_qpc_to_nwb,
    default_status=DefaultSensorStatus.STOPPED,
    minimum_interval_seconds=600,
)
def qpc_raw_data_file_sensor(context: SensorEvaluationContext):
    """Check for new QPC experiments.

    The creation of QPC rCells requires both the metadata in the google sheet
    and the raw/meta data files. This sensor checks for new experiments in the
    google sheet and checks that the raw data files are available.
    """

    # Find new experiments in the google sheet
    GS.update()

    new_job_ids_in_gs = set(
        str(job_id) for job_id in GS.job_ids if job_id_is_new(job_id, context)
    )

    # Find all raw data folders
    experiment_folders = list(CONFIG.dir.data.glob("*/Exp*/"))

    job_ids_in_data = [folder.name[3:] for folder in experiment_folders]
    job_ids_in_data = set(job_id for job_id in job_ids_in_data if job_id.isnumeric())

    new_job_ids = sorted(new_job_ids_in_gs.intersection(job_ids_in_data))

    new_runs = [RunRequest(partition_key=job_id) for job_id in new_job_ids]

    return SensorResult(
        run_requests=new_runs,
        dynamic_partitions_requests=[qpc_partitions_def.build_add_request(new_job_ids)],
    )
