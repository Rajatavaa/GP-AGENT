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
#Test the Slack api wether its working or not
response = slack_tools[1].invoke({})
print(f"The response is {response}")
print(f"The result of salck calls: {slack_tools}")