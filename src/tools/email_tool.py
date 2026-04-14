import base64
import mimetypes
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
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


def send_html_email(
    to: str, subject: str, message: str, attachment_path: str = None
) -> str:
    html_body = message.replace("\n", "<br>")

    if attachment_path:
        msg = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html_body, "html"))
        msg.attach(alt)

        filepath = os.path.expanduser(attachment_path)
        filename = os.path.basename(filepath)
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            mime_type = "application/octet-stream"
        maintype, subtype = mime_type.split("/", 1)

        with open(filepath, "rb") as f:
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(f.read())
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(attachment)
    else:
        msg = MIMEText(html_body, "html")

    msg["to"] = to
    msg["subject"] = subject
    encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me", body={"raw": encoded_message}
    ).execute()
    return f"Email sent to {to}"


email_tools = [
    GmailGetMessage(service=service),
    GmailSearch(service=service),
]
