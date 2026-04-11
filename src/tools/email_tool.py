import base64
from email.mime.text import MIMEText

from langchain_community.tools import GmailGetMessage, GmailSearch
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)

credentials = get_gmail_credentials(
    token_file="token.json",
    client_secrets_file="credentials.json",
)
service = build_resource_service(credentials=credentials)


def send_html_email(to: str, subject: str, message: str) -> str:
    html_body = message.replace("\n", "<br>")
    mime_message = MIMEText(html_body, "html")
    mime_message["to"] = to
    mime_message["subject"] = subject
    encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
    service.users().messages().send(
        userId="me", body={"raw": encoded_message}
    ).execute()
    return f"Email sent to {to}"


email_tools = [
    GmailGetMessage(service=service),
    GmailSearch(service=service),
]
