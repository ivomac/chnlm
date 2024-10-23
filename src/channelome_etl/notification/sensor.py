import os

from channelome_etl.igor.asset import extract_igor_to_nwb
from channelome_etl.notification.email import send_email_notification
from channelome_etl.notification.slack import send_slack_notification
from channelome_etl.qpc.asset import extract_qpc_to_nwb
from channelome_etl.syncropatch.asset import extract_syncropatch_to_nwb
from dagster import (
    DagsterEventType,
    DagsterRunStatus,
    DefaultSensorStatus,
    EventRecordsFilter,
    RunFailureSensorContext,
    RunStatusSensorContext,
    run_failure_sensor,
    run_status_sensor,
)
from dagster_slack import SlackResource


def get_email_subject(context) -> str:
    id = context.dagster_run.tags.get("dagster/partition")

    subject = ""
    if id is not None:
        status = context.dagster_run.status.value
        robot = context.dagster_run.job_name.split("_")[1].upper()

        subject = f"{robot} conversion of ID {id}: {status}"

    return subject


def get_message(context) -> str:
    if context.dagster_run.status.value == "FAILURE":
        return get_error_message(context)

    # Query the event log for STEP_OUTPUT events
    event_records = context.instance.get_event_records(
        EventRecordsFilter(
            event_type=DagsterEventType.STEP_OUTPUT,
        ),
        limit=1,
    )

    # Extract the output metadata
    output_metadata = {}
    for event_record in event_records:
        event = event_record.event_log_entry.dagster_event
        print(context.log.info(event))
        if event.event_specific_data and hasattr(event.event_specific_data, "metadata"):
            output_metadata.update(event.event_specific_data.metadata)

    message = output_metadata["message"].text if output_metadata else ""
    
    return message


def get_error_message(context) -> str:
    body = "\n"
    for event in context.get_step_failure_events():
        if getattr(event.event_specific_data.error, "cause", None):
            body += f"{event.event_specific_data.error.cause.to_string()}\n"
        else:
            body += f"{event.event_specific_data.error.to_string()}\n"
    return body


def get_email_body(context) -> str:
    id = context.dagster_run.tags.get("dagster/partition")
    body = ""
    if id is not None:
        base_url = os.environ["BASE_URL"]
        url = f"{base_url}/runs/{context.dagster_run.run_id}"

        body = "<pre>\n"
        body += f"<a href='{url}'>Dagster Report</a>\n"

        body += get_message(context)
        body += "</pre>"

    return body


def get_body(context) -> str:
    body = "- Robot: "
    if context.dagster_run.tags.get("dagster/partition") is not None:
        if context.dagster_run.job_name == "extract_qpc_to_nwb":
            body += "QPC"
        elif context.dagster_run.job_name == "extract_syncropatch_to_nwb":
            body += "Syncropatch"
        else:
            body += "Igor"
        body += f"\n- Experiment: {context.dagster_run.tags.get('dagster/partition')}"
        body += f"\n- Status: {context.dagster_run.status.value}"
        body += (
            f"\n<{os.getenv('BASE_URL')}/runs/{context.dagster_run.run_id}|"
            + "*Have a look at dagster webserver*>"
        )
        body += get_message(context)
    return body


def get_subject(context) -> str:
    subject = ""
    if context.dagster_run.tags.get("dagster/partition") is not None:
        if context.dagster_run.job_name in [
            "extract_qpc_to_nwb",
            "extract_syncropatch_to_nwb",
            "extract_igor_to_nwb",
        ]:
            subject = "--------------CONVERSION--------------"
            if context.dagster_run.status.value == "FAILURE":
                subject += ":cry:"
            else:
                subject += ":smile:"
    return subject


def get_channel(job_name) -> str:
    if job_name in ["extract_qpc_to_nwb", "extract_igor_to_nwb"]:
        return os.getenv("SLACK_CHANNEL_HERVE", "")
    return os.getenv("SLACK_CHANNEL", "")


def send_notification(context, slack):
    if os.getenv("NOTIFICATION") == "email":
        subject = get_email_subject(context)
        body = get_email_body(context)
        send_email_notification(subject, body)
    else:
        subject = get_subject(context)
        body = get_body(context)
        channel = get_channel(context.dagster_run.job_name)
        send_slack_notification(
            slack,
            channel,
            subject,
            body,
        )
    return subject, body


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[
        extract_qpc_to_nwb,
        extract_syncropatch_to_nwb,
        extract_igor_to_nwb,
    ],
    minimum_interval_seconds=10,
    default_status=DefaultSensorStatus.STOPPED,
)
def conversion_job_success(context: RunStatusSensorContext, slack: SlackResource):
    subject, body = send_notification(context, slack)

    context.log.info(context.resources)
    context.log.info(context.dagster_run.tags.get("dagster/partition"))
    context.log.info(subject)
    context.log.info(body)
    return


@run_failure_sensor(
    minimum_interval_seconds=10, default_status=DefaultSensorStatus.STOPPED
)
def job_run_failure(context: RunFailureSensorContext, slack: SlackResource):
    send_notification(context, slack)

    context.log.info(context.dagster_run)
    return
