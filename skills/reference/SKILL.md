---
name: simplex-reference
description: "Reference for the Simplex browser automation CLI and Python SDK. Use when the user mentions Simplex, simplex CLI, simplex editor, simplex connect, browser automation workflows, or wants to create/run/stream browser sessions. Also use when you see simplex commands, SIMPLEX_API_KEY, or imports from the simplex package."
allowed-tools: Bash, Read, Grep, Glob
---

# Simplex CLI & SDK Reference

Simplex is a browser automation platform. Users define workflows (name + URL + optional variables), then run them as browser sessions controlled by an AI agent. The CLI and Python SDK let you create workflows, start sessions, stream live events, and send messages to the agent.

## Installation

```bash
pip install simplex
```

This installs both the Python SDK (`from simplex import SimplexClient`) and the CLI (`simplex` command).

## Authentication

```bash
# Option 1: Environment variable
export SIMPLEX_API_KEY="your-api-key"

# Option 2: Login command (saves to ~/.simplex/credentials)
simplex login
```

To point at a different environment:
```bash
export SIMPLEX_BASE_URL="https://your-custom-api-url.example.com"
```

## CLI Commands

### `simplex editor` — Create a workflow and start an interactive editor session

```bash
simplex editor --name "My Workflow" --url "https://example.com"
simplex editor -n "My Workflow" -u "https://example.com" --var key=value
simplex editor --name "Test" --url "https://example.com" --json
```

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--name` | `-n` | Yes | Workflow name |
| `--url` | `-u` | Yes | Starting URL |
| `--var` | `-v` | No | Test data variable as key=value (repeatable) |
| `--json` | | No | Output raw JSON events (one per line, for piping) |

Creates a workflow, starts a browser session, and streams live agent events. Prints session info (session_id, workflow_id, vnc_url, logs_url, message_url) then streams SSE events until Ctrl+C.

### `simplex connect` — Stream events from a running session

```bash
simplex connect <session_id_or_logs_url>
simplex connect "https://host:port/stream" --json
```

| Argument | Description |
|----------|-------------|
| `session_id` or URL | Session ID to look up, or a logs_url directly |
| `--json` | Output raw JSON events |

### `simplex run` — Run an existing workflow

```bash
simplex run <workflow_id>
simplex run <workflow_id> --var email=test@test.com --watch
```

| Flag | Short | Description |
|------|-------|-------------|
| `--var` | `-v` | Variable as key=value (repeatable) |
| `--metadata` | `-m` | Metadata string |
| `--webhook-url` | | Webhook URL for status updates |
| `--watch` | `-w` | Poll until completion |

### `simplex pause` / `simplex resume`

```bash
simplex pause <session_id>
simplex resume <session_id>
```

### `simplex workflows list`

```bash
simplex workflows list --name "search term"
simplex workflows list --metadata "filter"
```

### `simplex sessions status` / `logs` / `download` / `replay`

```bash
simplex sessions status <session_id>
simplex sessions logs <session_id>
simplex sessions download <session_id> --filename report.pdf --output ./report.pdf
simplex sessions replay <session_id> --output replay.mp4
```

### `simplex login` / `whoami` / `logout`

```bash
simplex login       # Prompts for API key, saves to ~/.simplex/credentials
simplex whoami      # Shows current auth status
simplex logout      # Removes saved credentials
```

## Python SDK

```python
from simplex import SimplexClient

client = SimplexClient(api_key="your-key")
# Or with custom base URL:
client = SimplexClient(api_key="your-key", base_url="https://custom-url.com")
```

### Workflow Management

```python
# Create a workflow
result = client.create_workflow(name="My Workflow", url="https://example.com")
workflow_id = result["workflow"]["id"]

# Get a workflow
workflow = client.get_workflow(workflow_id)
# Returns: {"succeeded": true, "workflow": {"id": "...", "name": "...", ...}}

# Update a workflow
client.update_workflow(workflow_id, name="New Name", url="https://new-url.com")

# Search workflows
results = client.search_workflows(workflow_name="search term")
# Returns: {"succeeded": true, "workflows": [...], "count": N}
```

### Editor Sessions (Interactive)

```python
# Start an editor session (creates workflow + browser session)
result = client.start_editor_session(
    name="My Session",
    url="https://example.com",
    test_data={"username": "test"},  # optional variables
)
# Returns: succeeded, workflow_id, session_id, vnc_url, logs_url, message_url, filesystem_url
# NOTE: This call takes 30-40 seconds. Use timeout=120 on the client.

# Stream live SSE events
for event in client.stream_session(result["logs_url"]):
    event_type = event.get("event") or event.get("type", "")
    print(f"[{event_type}] {event}")

# Send a message to the agent
client.send_message(result["message_url"], "Click the login button")

# Close the session
client.close_session(result["session_id"])
```

### Run Existing Workflows

```python
result = client.run_workflow("workflow-id", variables={"key": "value"})
session_id = result["session_id"]

# Poll for completion
import time
while True:
    status = client.get_session_status(session_id)
    if not status["in_progress"]:
        break
    time.sleep(2)

if status["success"]:
    print(status["scraper_outputs"])
    print(status["structured_output"])
```

### Session Management

```python
client.pause(session_id)
client.resume(session_id)
client.close_session(session_id)
client.get_session_status(session_id)
client.retrieve_session_logs(session_id)      # Returns parsed logs (None if still running)
client.download_session_files(session_id)       # Returns bytes (zip)
client.retrieve_session_replay(session_id)      # Returns bytes (mp4)
```

## SSE Event Format

Events from `stream_session()` are dicts. The event type is in the `event` key (not `type`):

| Event | Description | Key Fields |
|-------|-------------|------------|
| `RunContent` | Agent text output | `content`, `content_type`, `session_id` |
| `ToolCallStarted` | Tool invocation | `tool` (object with `tool_name`, `tool_args`) |
| `ToolCallCompleted` | Tool result | `tool` (object with `content` result) |
| `FlowPaused` | Session paused | `pause_key`, `pause_id` |
| `FlowResumed` | Session resumed | `pause_key` |
| `RunCompleted` | Agent finished | `content`, `session_id` |
| `RunError` | Error occurred | `content` (error message) |

The `message_url` can be derived from `logs_url` by replacing `/stream` with `/message`.

## Common Patterns

### Pipe JSON events to another tool
```bash
simplex editor -n "Test" -u "https://example.com" --json | jq '.event'
```

### Start a session and get the URLs for later use
```bash
simplex editor -n "Test" -u "https://example.com" --json | head -1
# First line is: {"type": "SessionStarted", "session_id": "...", "logs_url": "...", ...}
```

### Use in scripts
```python
import os
from simplex import SimplexClient

client = SimplexClient(
    api_key=os.environ["SIMPLEX_API_KEY"],
    base_url=os.environ.get("SIMPLEX_BASE_URL", "https://api.simplex.sh"),
    timeout=120,  # Important: editor sessions take 30-40s to start
)
```
