# Test 05: SSE Streaming Scenarios

## Setup

```bash
export SIMPLEX_API_KEY="your-api-key-here"
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
```

## Test 5A: stream_session yields correct event structure

```python
from simplex import SimplexClient

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,
)

# Start a session first
result = client.start_editor_session(name="Stream Test", url="https://example.com")
logs_url = result["logs_url"]

# Stream events
event_types_seen = set()
for event in client.stream_session(logs_url):
    event_type = event.get("event") or event.get("type", "unknown")
    event_types_seen.add(event_type)
    print(f"[{event_type}] {str(event)[:200]}")

    # Collect a few events then stop
    if len(event_types_seen) >= 3:
        break

print(f"\nEvent types seen: {event_types_seen}")
```

**Expected:** Each event is a dict with an "event" field (the event type). Common types:
- `RunContent` - Agent text output
- `ToolCallStarted` - Tool invocation beginning
- `ToolCallCompleted` - Tool result
- `FlowPaused` - Session paused for input
- `RunCompleted` / `RunFinished` - Session done
- `RunError` - Error occurred

## Test 5B: SSE stream handles disconnection gracefully

```python
import signal

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,
)

result = client.start_editor_session(name="Disconnect Test", url="https://example.com")
logs_url = result["logs_url"]

try:
    count = 0
    for event in client.stream_session(logs_url):
        count += 1
        print(f"Event {count}: {event.get('type', 'unknown')}")
        if count >= 5:
            print("Breaking out of stream...")
            break
except Exception as e:
    print(f"Exception: {e}")

print("Clean exit after break")
# Close the session
client.close_session(result["session_id"])
```

**Expected:** Breaking out of the generator loop is clean, no hanging connections.

## Test 5C: SSE stream with API key auth (not token)

The SSE /stream endpoint on the container now supports API key auth.
This is verified implicitly by `stream_session` working, since the SDK always uses API key auth.

```python
# This test is implicitly covered by all stream_session calls.
# The HttpClient.session has X-API-Key header set, and the /stream
# endpoint accepts it.
```

## Test 5D: send_message to a live session

```python
client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,
)

result = client.start_editor_session(name="Message Test", url="https://example.com")
message_url = result.get("message_url")
session_id = result["session_id"]

if message_url:
    # Send a message
    response = client.send_message(message_url, "Navigate to the about page")
    print(f"Send response: {response}")
else:
    print("No message_url returned (container may still be initializing)")

# Clean up
client.close_session(session_id)
```

**Expected:** Message is accepted by the container. The `/message` endpoint now supports API key auth.

## Test 5E: send_message with API key auth (verifies /message auth fix)

This is the key test for the `modal_browser.py` change. Previously `/message` only accepted token auth. Now it also accepts API key.

```python
import requests

# Direct HTTP request to verify API key auth on /message
message_url = "<message_url from start_editor_session>"
api_key = "YOUR_KEY"

response = requests.post(
    message_url,
    json={"message": "test message"},
    headers={"X-API-Key": api_key},
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

**Expected:** 200 OK. Previously this would have returned 401/403 without a bearer token.

## Test 5F: CLI connect streams events from editor session

Two terminal windows needed:

**Terminal 1:**
```bash
simplex editor --name "Dual Terminal Test" --url "https://example.com" --json | head -1
# Copy the logs_url from the first JSON line
```

**Terminal 2:**
```bash
simplex connect "<logs_url_from_terminal_1>"
```

**Expected:** Terminal 2 receives the same events as Terminal 1.

## Test 5G: Malformed SSE data handling

```python
# The stream_sse method in _http_client.py skips lines that aren't
# valid JSON after "data: ". This test verifies no crash on bad data.
# (This is mostly an implementation safety check)
```

**Expected:** Invalid JSON lines in the SSE stream are silently skipped.
