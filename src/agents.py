from langchain.agents import initialize_agent, AgentType
from langchain_core.messages import HumanMessage

def create_agent(llm,tools):
    agent = initialize_agent(llm=llm,
                             tools=tools,
                             agent=AgentType.OPENAI_FUNCTIONS,
                             verbose=True)
    return agent

def agent_node(state,agent):
    user_input = state.get(input," ")
    result = agent.run(user_input)
    return {**state,"output":result}

def slack_agent(state,agent):
    "Agent specialized for slack"
    user_input = state.get(input," ")
    result = agent.run(f"You are an agent that knows how to use Slack. Handle this request \n{user_input}")
    return {**state,"output":result}

def email_agent(state,agent):
    "Agent specialized for email"
    user_input = state.get(input," ")
    result = agent.run(f"You are an agent that knows how to use Gmail. Handle this request \n{user_input}")
    return {**state,"output":result}

#This is the fallback if the previous agent nodes fails
def general_agent_node(state, agent):
    """
    Fallback agent
    """
    user_input = state.get("input", "")

    result = agent.run(
        f"You are a helpful assistant. Handle this:\n{user_input}"
    )

    return {
        **state,
        "output": result,
    }

def router(state,llm):
    user_input = state[input].lower()

    if 'slack' in user_input:
        return "slack"
    if "email" in user_input:
        return "email"

    prompt = f"""
    Classify intent: email, slack, or general.

    Input: {user_input}
    """
    return llm.invoke(prompt).content.strip().lower()

def format_output(state):
    """
    Final output formatter
    """
    return {
        "final_output": state.get("output", "")
    }