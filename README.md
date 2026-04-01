# GP-AGENT

A multi-agent system built with **LangGraph** and **LangChain** that intelligently routes user requests to specialized agents for **Email (Gmail)**, **Slack**, and **General Chat** operations. Powered by a local LLM server.

---

## Architecture

```
User Input → Router (intent classification)
                 ├── "email" → Email Agent (Gmail: send, search, read)
                 ├── "slack" → Slack Agent (send message, get channels/messages)
                 └── "general" → General Agent (plain LLM response)
```

The **Router** uses keyword matching first (fast path), then falls back to LLM classification for ambiguous inputs. Each agent executes domain-specific logic with integrated tools and returns the result.

---

## Project Structure

```
GP-AGENT/
├── main.py                  # Entry point - initializes LLM, agents, runs the graph
├── pyproject.toml           # Project metadata and dependencies
├── .python-version          # Python 3.11
└── src/
    ├── __init__.py
    ├── agents.py            # Router, email/slack/general agent logic
    ├── graphs.py            # LangGraph state graph definition
    └── tools/
        ├── email_tool.py    # Gmail API tools (Send, Search, Get)
        └── slack_tool.py    # Slack API tools (Send, GetChannel, GetMessage)
```

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **A local LLM server** running on `http://localhost:8000/v1` with an OpenAI-compatible API (e.g., [llama.cpp](https://github.com/ggml-org/llama.cpp), [vLLM](https://github.com/vllm-project/vllm), or [Ollama](https://ollama.com/))
- **Google Cloud Project** with Gmail API enabled (for email features)
- **Slack User Token** (for Slack features)

---

## Installation

```bash
git clone <repository-url>
cd GP-AGENT
```

**Using uv (recommended):**

```bash
uv venv && source .venv/bin/activate
uv sync
```

**Using pip:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

---

## Configuration

### 1. Local LLM Server

Start a local LLM server before running the agent. Examples:

```bash
# llama.cpp
llama-server -m your-model.gguf --port 8000

# vLLM
vllm serve your-model --port 8000

# Ollama (change base_url in main.py to http://localhost:11434/v1)
ollama serve
```

To change the endpoint, edit `base_url` in `main.py` line 7.

### 2. Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API** (APIs & Services > Library)
3. Create **OAuth 2.0 credentials** (APIs & Services > Credentials > OAuth client ID > Desktop application)
4. Download and rename the file to `credentials.json`, place it in the project root
5. On first run, a browser window opens for authorization. A `token.json` is created automatically for subsequent runs.

> Both `credentials.json` and `token.json` are git-ignored. Never commit these.

### 3. Slack Token Setup

1. Go to [Slack API Apps](https://api.slack.com/apps) and create/select an app
2. Add OAuth scopes: `channels:read`, `chat:write`, `channels:history`
3. Install to your workspace and copy the **User OAuth Token** (`xoxp-...`)
4. Create a `.env` file in the project root:

```env
SLACK_USER_TOKEN=xoxp-your-token-here
```

---

## Usage

```bash
python main.py
```

By default, `main.py` runs a hardcoded example query. Edit line 16 to change the input:

```python
result = graph.invoke({"input": "Your query here"})
```

### Examples

```python
# Send email
graph.invoke({"input": "Send an email to john@example.com saying The meeting is rescheduled to Friday"})

# Send email with explicit subject
graph.invoke({"input": "Send an email to jane@example.com about Project Update saying Sprint is on track"})

# Read emails
graph.invoke({"input": "Read emails from boss@company.com"})

# Slack message
graph.invoke({"input": "Send a slack message to #general saying Deployment complete"})

# General question
graph.invoke({"input": "What is the capital of France?"})
```

---

## Troubleshooting

- **"Connection refused"** - Your local LLM server isn't running. Start it before running the agent.
- **Gmail auth errors** - Ensure `credentials.json` exists. Delete `token.json` to re-authenticate.
- **Slack errors** - Check your `.env` file has a valid `SLACK_USER_TOKEN`. Note: `slack_tool.py` runs a test call on import, so errors show immediately.
- **Wrong routing** - Include "email" or "slack" in your query for reliable routing. Ambiguous queries depend on your local model's accuracy.
- **Email fields wrong** - Use `saying` before the body, and `about`/`regarding`/`on` before the subject for best extraction.
