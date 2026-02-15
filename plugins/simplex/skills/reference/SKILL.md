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
simplex editor -n "Test" -u "https://example.com" --vars '{"email":"a@b.com","name":"Test"}'
simplex editor -n "Test" -u "https://example.com" --vars data.json
simplex editor --name "Test" --url "https://example.com" --json
```

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--name` | `-n` | Yes | Workflow name |
| `--url` | `-u` | Yes | Starting URL |
| `--vars` | | No | Variables as inline JSON string or path to a .json file |
| `--json` | | No | Output raw JSON events (one per line, for piping) |

Creates a workflow and starts a browser session. Shows a panel with the workflow link, session ID, and VNC URL, then returns. Use `simplex connect <name>` to stream events and `simplex send <name> "message"` to interact.

### `simplex connect` — Stream events from a running session

```bash
simplex connect "My Workflow"             # Resolve by workflow name (partial match)
simplex connect <workflow_id>             # Look up active session by workflow ID
simplex connect "https://host:port/stream" --json
```

| Argument | Description |
|----------|-------------|
| `target` | **Required.** Workflow name, workflow ID, or logs URL |
| `--json` | Output raw JSON events |

The target is resolved via the API: if it doesn't look like a UUID, `search_workflows` is called to match by name.

### `simplex run` — Run an existing workflow

```bash
simplex run <workflow_id>
simplex run <workflow_id> --vars '{"email":"test@test.com","zip":"91711"}' --watch
simplex run <workflow_id> --vars variables.json --watch
```

| Flag | Short | Description |
|------|-------|-------------|
| `--vars` | | Variables as inline JSON string or path to a .json file |
| `--metadata` | `-m` | Metadata string |
| `--webhook-url` | | Webhook URL for status updates |
| `--watch` | `-w` | Poll until completion |

### `simplex send` — Send a message to a running session

```bash
simplex send "My Workflow" "Click the login button"     # Resolve by name
simplex send <workflow_id> "Fill in the email"
```

| Argument | Description |
|----------|-------------|
| `target` | **Required.** Workflow name or workflow ID |
| `message` | **Required.** Message to send to the browser agent |

The target is resolved via the API: if it doesn't look like a UUID, `search_workflows` is called to match by name.

### `simplex editor-interrupt` — Interrupt a running editor session

```bash
simplex editor-interrupt "My Workflow"    # By workflow name
simplex editor-interrupt <workflow_id>    # By workflow ID
```

Sends an interrupt signal to the editor session's agent, stopping it mid-execution. The agent pauses and emits an SSE event. Accepts workflow name (resolved via API) or workflow ID.

### `simplex pause` / `simplex resume`

```bash
simplex pause <session_id>
simplex resume <session_id>
```

### `simplex workflows list`

```bash
simplex workflows list                       # List all workflows
simplex workflows list --name "search term"  # Filter by name
simplex workflows list --metadata "filter"   # Filter by metadata
```

### `simplex workflows vars` — Show variable schema for a workflow

```bash
simplex workflows vars <workflow_id>
simplex workflows vars <workflow_id> --json
```

Displays a table of the workflow's variable definitions including name, type, whether it's required, default value, and allowed enum values. Also prints an example run command with the required variables.

### `simplex sessions status` / `logs` / `download` / `replay`

```bash
simplex sessions status <session_id>
simplex sessions logs <session_id>
simplex sessions download <session_id> --filename report.pdf --output ./report.pdf
simplex sessions replay <session_id> --output replay.mp4
```

### `simplex login` / `whoami` / `logout`

```bash
simplex login       # Prompts for API key (masked with *), saves to ~/.simplex/credentials
simplex whoami      # Shows current auth status
simplex logout      # Removes saved credentials
```

## Variable Input Formats

Variables are passed via `--vars` as inline JSON or a file path:

```bash
# Inline JSON — supports objects, arrays, numbers, booleans
simplex run <id> --vars '{"email":"test@test.com","count":5,"address":{"street":"742 Market St","city":"SF"}}'

# JSON file
simplex run <id> --vars my-variables.json
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

# Get a workflow (includes variable definitions)
workflow = client.get_workflow(workflow_id)
# Returns: {"succeeded": true, "workflow": {"id": "...", "name": "...", "variables": [...], ...}}

# Update a workflow
client.update_workflow(workflow_id, name="New Name", url="https://new-url.com")

# List all workflows (no args) or search by name/metadata
results = client.search_workflows()                          # all workflows
results = client.search_workflows(workflow_name="search term")  # filter by name
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
# NOTE: This call takes 10-15 seconds. Use timeout=120 on the client.

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

# Get active session for a workflow
client.get_workflow_active_session(workflow_id)
# Returns: {"session_id": "...", "status": "...", "logs_url": "...", "message_url": "...", "vnc_url": "..."}
```

## SSE Event Format

Events from `stream_session()` are dicts. The event type is in the `event` key (not `type`):

| Event | Description | Key Fields |
|-------|-------------|------------|
| `RunStarted` | Agent started | `session_id` |
| `RunContent` | Agent text output | `content`, `content_type`, `session_id` |
| `ToolCallStarted` | Tool invocation | `tool` (object with `tool_name`, `tool_args`) |
| `ToolCallCompleted` | Tool result | `tool` (object with `content` result, `tool_call_error` bool) |
| `FlowPaused` | Session paused | `pause_key`, `pause_id`, `pause_type`, `prompt` |
| `FlowResumed` | Session resumed | `pause_key` |
| `AskUserQuestion` | Agent needs user input | `data.tool_use_id`, `data.questions[]` (see below) |
| `RunCompleted` | Agent finished | `content`, `session_id`, `metrics` (with `duration_ms`) |
| `RunError` | Error occurred | `content` (error message) |

The `message_url` can be derived from `logs_url` by replacing `/stream` with `/message`.

### AskUserQuestion Event — Human-in-the-loop Bridge

When the browser agent needs user input, it emits an `AskUserQuestion` SSE event. **When streaming a Simplex session from Claude Code, you MUST bridge this to Claude Code's own `AskUserQuestion` tool so the user can respond interactively.**

#### Event format
```json
{
  "event": "AskUserQuestion",
  "data": {
    "tool_use_id": "toolu_01BuAY2hQm288WTZhfPqPEnn",
    "questions": [
      {
        "question": "Which form field did you mean?",
        "header": "Clarify",
        "options": [
          {"label": "Name field", "description": "The patient name input"},
          {"label": "DOB field", "description": "The date of birth input"}
        ],
        "multiSelect": false
      }
    ]
  }
}
```

#### How to handle in Claude Code

1. **Detect** the `AskUserQuestion` event while iterating over `simplex connect --json` output or SDK `stream_session()`.
2. **Call the `AskUserQuestion` tool** with the `questions` array directly from `data.questions`. The schema is identical — pass `questions` as-is.
3. **Read the user's answer** from the tool result. The answer object maps string question indices to the selected option label, e.g. `{"0": "Name field"}`.
4. **Send the answer back** via `simplex send` or `POST /message`:
   ```bash
   simplex send <target> '{"type":"ask_user_answer","tool_use_id":"toolu_01BuAY2hQm288WTZhfPqPEnn","answers":{"0":"Name field"}}'
   ```
   Or with the SDK:
   ```python
   client.send_message(message_url, json.dumps({
       "type": "ask_user_answer",
       "tool_use_id": "toolu_01BuAY2hQm288WTZhfPqPEnn",
       "answers": {"0": "Name field"}
   }))
   ```

#### Key details
- `questions` is an array (usually 1, max 4)
- Each question has 2-4 `options`
- `multiSelect: true` means multiple options can be selected (comma-separated labels)
- Answer keys are string indices (`"0"`, `"1"`) mapping to the selected option `label`
- Free-text answers work too — if the user picks "Other", send their raw text as the answer value

## Common Patterns

### Pass many variables via JSON file
```bash
cat > vars.json << 'EOF'
{
  "business_name": "Acme Plumbing",
  "zip_code": "94103",
  "email": "contact@acme.com",
  "annual_revenue": 500000
}
EOF
simplex run <workflow_id> --vars vars.json --watch
```

### Check what variables a workflow needs before running
```bash
simplex workflows vars <workflow_id>
```

### Start a session, then connect and interact
```bash
simplex editor -n "My Flow" -u "https://example.com"
# Returns immediately with workflow ID + link

# In another terminal:
simplex connect "My Flow"                                # Stream live events
simplex send "My Flow" "Click the login button"          # Send a message
```

### Get session URLs for programmatic use
```bash
simplex editor -n "Test" -u "https://example.com" --json
# Outputs: {"type": "SessionStarted", "session_id": "...", "workflow_id": "...", "logs_url": "...", ...}
```

### Pipe JSON events to another tool
```bash
simplex connect "My Flow" --json | jq '.event'
```

### Use in scripts
```python
import os
from simplex import SimplexClient

client = SimplexClient(
    api_key=os.environ["SIMPLEX_API_KEY"],
    base_url=os.environ.get("SIMPLEX_BASE_URL", "https://api.simplex.sh"),
    timeout=120,  # Important: editor sessions take 10-15s to start
)
```
