# Simplex Python SDK & CLI

Official Python SDK and CLI for the [Simplex](https://simplex.sh) browser automation platform.

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

## Claude Code Plugin

Give Claude Code full knowledge of the Simplex CLI and SDK:

```
/plugin install simplexlabs/simplex-python
```

Once installed, Claude Code automatically knows how to use `simplex editor`, `simplex connect`, `simplex run`, and the full Python SDK.

## CLI

### `simplex editor` — Create a workflow and start an interactive session

```bash
simplex editor --name "My Workflow" --url "https://example.com"
simplex editor -n "My Workflow" -u "https://example.com" --var key=value
simplex editor -n "Test" -u "https://example.com" --json
```

Creates a workflow, starts a browser session, and streams live agent events. Prints session info (session_id, workflow_id, vnc_url) then streams SSE events until Ctrl+C.

### `simplex connect` — Stream events from a running session

```bash
simplex connect <session_id>
simplex connect "https://host:port/stream" --json
```

### `simplex run` — Run an existing workflow

```bash
simplex run <workflow_id>
simplex run <workflow_id> --var email=test@test.com --watch
```

### `simplex pause` / `simplex resume`

```bash
simplex pause <session_id>
simplex resume <session_id>
```

### `simplex workflows list`

```bash
simplex workflows list --name "search term"
```

### `simplex sessions`

```bash
simplex sessions status <session_id>
simplex sessions logs <session_id>
simplex sessions download <session_id> --filename report.pdf --output ./report.pdf
simplex sessions replay <session_id> --output replay.mp4
```

### `simplex login` / `whoami` / `logout`

```bash
simplex login       # Prompts for API key
simplex whoami      # Shows current auth status
simplex logout      # Removes saved credentials
```

## Python SDK

### Quick Start

```python
from simplex import SimplexClient

client = SimplexClient(api_key="your-api-key")

# Start an interactive editor session
result = client.start_editor_session(
    name="My Session",
    url="https://example.com",
    test_data={"username": "test"},
)
print(f"Session: {result['session_id']}")
print(f"VNC: {result['vnc_url']}")

# Stream live events
for event in client.stream_session(result["logs_url"]):
    print(event)

# Send a message to the agent
client.send_message(result["message_url"], "Click the login button")

# Close the session
client.close_session(result["session_id"])
```

### Client

```python
client = SimplexClient(
    api_key="your-api-key",
    base_url="https://api.simplex.sh",  # Optional
    timeout=30,                          # Request timeout in seconds
    max_retries=3,                       # Retry attempts
    retry_delay=1.0,                     # Delay between retries
)
```

### Workflow Management

```python
# Create
result = client.create_workflow(name="My Workflow", url="https://example.com")
workflow_id = result["workflow"]["id"]

# Get
workflow = client.get_workflow(workflow_id)

# Update
client.update_workflow(workflow_id, name="New Name", url="https://new-url.com")

# Search
results = client.search_workflows(workflow_name="search term")
```

### Editor Sessions

```python
# Start an editor session (creates workflow + browser session)
# NOTE: Takes 10-15 seconds. Use timeout=120.
result = client.start_editor_session(
    name="My Session",
    url="https://example.com",
    test_data={"username": "test"},
)
# Returns: succeeded, workflow_id, session_id, vnc_url, logs_url, message_url, filesystem_url

# Stream live SSE events
for event in client.stream_session(result["logs_url"]):
    event_type = event.get("event") or event.get("type", "")
    print(f"[{event_type}] {event}")

# Send a message to the agent
client.send_message(result["message_url"], "Click the login button")
```

### Run Workflows

```python
import time

result = client.run_workflow("workflow-id", variables={"key": "value"})

# Poll for completion
while True:
    status = client.get_session_status(result["session_id"])
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
client.retrieve_session_logs(session_id)
client.download_session_files(session_id)
client.retrieve_session_replay(session_id)
```

## SSE Event Format

Events from `stream_session()` are dicts. The event type is in the `event` key:

| Event | Description |
|-------|-------------|
| `RunContent` | Agent text output |
| `ToolCallStarted` | Tool invocation started |
| `ToolCallCompleted` | Tool result |
| `FlowPaused` | Session paused |
| `FlowResumed` | Session resumed |
| `RunCompleted` | Agent finished |
| `RunError` | Error occurred |

## Error Handling

```python
from simplex import (
    SimplexError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    ValidationError,
    WorkflowError,
)

try:
    result = client.run_workflow("workflow-id")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except WorkflowError as e:
    print(f"Workflow error: {e.message}, session: {e.session_id}")
except SimplexError as e:
    print(f"Error: {e.message}")
```

## Requirements

- Python 3.9+
- `requests>=2.25.0`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Simplex](https://simplex.sh)
- [Documentation](https://docs.simplex.sh)
- [Support](mailto:support@simplex.sh)
