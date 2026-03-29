from langchain_community.tools import GmailGetMessage, GmailSearch, GmailSendMessage
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)

credentials = get_gmail_credentials(
    token_file="token.json",
    client_secrets_file="credentials.json",
)
service = build_resource_service(credentials=credentials)
email_tools = [
    GmailSendMessage(service=service),
    GmailGetMessage(service=service),
    GmailSearch(service=service),
]
