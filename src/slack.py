from dotenv import load_dotenv
import os
from langchain_community.tools import SlackGetChannel, SlackGetMessage, SlackSendMessage 

load_dotenv()

SLACK_SECRET = os.getenv("SLACK_USER_TOKEN")
slack_tools = [
    SlackSendMessage(slack_token=SLACK_SECRET),
    SlackGetChannel(slack_token=SLACK_SECRET),
    SlackGetMessage(slack_token=SLACK_SECRET),
]
