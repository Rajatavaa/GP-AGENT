from src.graphs import build_graph
from src.agents import start_agent
from src.tools.email_tool import email_tools
from src.tools.slack_tool import slack_tools
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(base_url="http://localhost:8000/v1", api_key="sk-no-key-needed")


email_agent = start_agent(llm, email_tools)
slack_agent = start_agent(llm, slack_tools)
general_agent = start_agent(llm, [])

graph = build_graph(email_agent, slack_agent, general_agent, llm).compile()

result = graph.invoke({"input": "Send an email to rajatava@aivctalent.com saying The recent agentic project was wondeful and adds a lot of value"})

print(result["output"])
