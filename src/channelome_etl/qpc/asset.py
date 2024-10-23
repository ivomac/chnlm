from dagster import (
    AssetExecutionContext,
    DynamicPartitionsDefinition,
    Output,
    asset,
    define_asset_job,
)
from qpc.conversion.rcell import RCell

qpc_partitions_def = DynamicPartitionsDefinition(name="qpc")


@asset(partitions_def=qpc_partitions_def)
def qpc_to_nwb(context: AssetExecutionContext):
    """Create rCells for QPC experiments. Only the first 3 reps are kept."""

    job_id = int(context.partition_key)

    cell = RCell(job_id)
    report = cell.create(overwrite=True, drop=True, keep_reps=3)

    assert cell.Exp.out.is_file(), "rCell not created"

    yield Output(
        job_id,
        output_name="result",
        metadata={
            "message": report,
        },
    )


extract_qpc_to_nwb = define_asset_job(
    name="extract_qpc_to_nwb",
    selection=["qpc_to_nwb"],
)
