# GP-AGENT

A multi-agent system built with **LangGraph** and **LangChain** that intelligently routes user requests to specialized agents for **Email (Gmail)**, **Slack**, and **General Chat** operations. Powered by a local LLM via an OpenAI-compatible API.

---

## Architecture

```
User Input (CLI)
    │
    ▼
  Router ── keyword match (fast path) ──┐
    │                                    │
    ▼ (ambiguous)                        │
  LLM classification                     │
    │                                    │
    ├── compose signals? ─► LLM Compose ─┤
    │       ("write", "professional",    │
    │        "in 50 words", etc.)        │
    │                                    │
    ▼                                    ▼
  ┌──────────────────────────────────────────┐
  │  "email"  → Email Agent (send / read)    │
  │  "slack"  → Slack Agent (send / read /   │
  │              list channels)              │
  │  "general"→ General Chat (plain LLM)     │
  └──────────────────────────────────────────┘
    │
    ▼
  Preview & Confirm (send / edit / cancel)
    │
    ▼
  Output (Rich formatted panel)
```

The **Router** uses keyword matching first (fast path), then falls back to LLM classification for ambiguous inputs. If compose signals are detected (e.g. "write a professional 50 word message"), the LLM drafts the message before routing to the target agent. All outgoing messages go through an interactive preview where you can **send**, **edit**, or **cancel**.

---

## Project Structure

```
GP-AGENT/
├── main.py                  # Interactive CLI entry point
├── pyproject.toml           # Project metadata and dependencies
├── config.json              # User config (sender name, auto-created)
├── .env.example             # Environment variable template
├── HOW-TO-RUN.md            # Quick-start guide
└── src/
    ├── __init__.py
    ├── agents.py            # Email, Slack, and general chat agent logic
    ├── graphs.py            # LangGraph state graph definition
    ├── router.py            # Intent classification (keyword + LLM fallback)
    ├── config.py            # Config file management (sender name)
    ├── utils.py             # Message composition, editing, subject generation
    ├── display.py           # Rich console output (banners, tables, panels)
    └── tools/
        ├── email_tool.py    # Gmail API tools (Send, Search, Get)
        └── slack_tool.py    # Slack API tools (Send, GetChannel, GetMessage)
```

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **A local LLM server** with an OpenAI-compatible API (e.g., [Ollama](https://ollama.com/), [llama.cpp](https://github.com/ggml-org/llama.cpp), [vLLM](https://github.com/vllm-project/vllm), or [LM Studio](https://lmstudio.ai/))
- **Google Cloud Project** with Gmail API enabled (for email features)
- **Slack App** with a User OAuth Token (for Slack features)

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

### 1. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Slack
SLACK_USER_TOKEN=xoxp-your-token-here

# LLM (optional, defaults shown)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
```

Any local LLM server that exposes an OpenAI-compatible API will work:

| Server | LLM_BASE_URL |
|---|---|
| Ollama | `http://localhost:11434/v1` |
| llama.cpp | `http://localhost:8000/v1` |
| vLLM | `http://localhost:8000/v1` |
| LM Studio | `http://localhost:1234/v1` |

### 2. Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API** (APIs & Services > Library)
3. Create **OAuth 2.0 credentials** (APIs & Services > Credentials > OAuth client ID > Desktop application)
4. Download and rename the file to `credentials.json`, place it in the project root
5. On first run, a browser window opens for authorization. A `token.json` is created automatically for subsequent runs.

> Both `credentials.json` and `token.json` are git-ignored. Never commit these.

### 3. Slack App Setup

1. Go to [Slack API Apps](https://api.slack.com/apps) and create a new app
2. Go to **OAuth & Permissions** and add these **User Token Scopes**:
   - `channels:read`
   - `channels:history`
   - `chat:write`
   - `users:read`
3. Install the app to your workspace
4. Copy the **User OAuth Token** (`xoxp-...`) into your `.env` file

---

## Usage

Start the LLM server, then run:

```bash
python main.py
```

On first run, you'll be prompted for your name (used in email sign-offs). This is saved to `config.json`.

### CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/info` | Display session info (model, uptime) |
| `/clear` | Clear the terminal |
| `/quit`, `/exit` | Exit the application |

Multi-line input is supported — end a line with `\` to continue on the next line. Command history is saved across sessions.

### Examples

```
> send a slack message to #general saying deployment complete
> write a professional 50 word slack message to #general about the release
> read slack messages from #general
> list my slack channels
> send an email to john@example.com saying the meeting is rescheduled
> write a formal email to jane@example.com about project update
> read my emails from boss@company.com
> what is machine learning?
```

When sending messages, you'll get a preview with options to **send**, **edit**, or **cancel** before anything is sent.

---

## Troubleshooting

- **"Cannot connect to LLM server"** — Your local LLM server isn't running. Start it before running the agent.
- **Gmail auth errors** — Ensure `credentials.json` exists. Delete `token.json` to re-authenticate.
- **"Slack token invalid"** — Check your `.env` file has a valid `SLACK_USER_TOKEN`.
- **Wrong routing** — Include "email" or "slack" in your query for reliable routing. Ambiguous queries fall back to LLM classification, whose accuracy depends on your local model.
- **Email fields wrong** — Use `saying` before the body, and `about`/`regarding`/`on` before the subject for best extraction.
- **Name not showing in emails** — Edit `config.json` in the project root, or delete it to be prompted again on next run.
