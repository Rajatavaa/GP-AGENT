from langchain_community.tools import GmailGetMessage,GmailSearch
from langchain_community.tools.gmail.utils import build_resource_service

service = build_resource_service()
tools = [GmailGetMessage(service=service),GmailSearch(service=service)]
