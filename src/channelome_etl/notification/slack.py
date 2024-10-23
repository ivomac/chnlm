from dagster_slack import SlackResource


def send_slack_notification(
    slack: SlackResource, channel: str, header: str, message: str
):
    slack.get_client().chat_postMessage(
        channel=f"#{channel}",
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header,
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
        ],
    )
