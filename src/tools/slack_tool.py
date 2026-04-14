import os

from dotenv import load_dotenv
from langchain_community.tools import SlackGetChannel, SlackGetMessage, SlackSendMessage
from slack_sdk import WebClient

load_dotenv()

SLACK_SECRET = os.getenv("SLACK_USER_TOKEN")
slack_client = WebClient(token=SLACK_SECRET)
slack_tools = [
    SlackSendMessage(slack_token=SLACK_SECRET),
    SlackGetChannel(slack_token=SLACK_SECRET),
    SlackGetMessage(slack_token=SLACK_SECRET),
]


def slack_upload_file(channel: str, file_path: str, message: str = "") -> str:
    filepath = os.path.expanduser(file_path)
    filename = os.path.basename(filepath)
    response = slack_client.files_upload_v2(
        channel=channel,
        file=filepath,
        title=filename,
        initial_comment=message or None,
    )
    return f"File '{filename}' uploaded to #{channel}"
