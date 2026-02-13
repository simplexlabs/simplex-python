# Test 07: End-to-End Flow

## Overview

This test covers the complete happy path: create an editor session, stream events, send a message, and close.

## Setup

```bash
export SIMPLEX_API_KEY="your-api-key-here"
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
```

## Test 7A: Full SDK flow

```python
import time
from simplex import SimplexClient

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,
)

# Step 1: Start editor session
print("Starting editor session...")
result = client.start_editor_session(
    name="E2E Test Workflow",
    url="https://news.ycombinator.com",
    test_data={"category": "front_page"},
)
assert result["succeeded"]
session_id = result["session_id"]
workflow_id = result["workflow_id"]
vnc_url = result["vnc_url"]
logs_url = result["logs_url"]
message_url = result.get("message_url")

print(f"Session:  {session_id}")
print(f"Workflow: {workflow_id}")
print(f"VNC:      {vnc_url}")
print(f"Logs:     {logs_url}")
print(f"Message:  {message_url}")

# Step 2: Verify workflow was created
workflow = client.get_workflow(workflow_id)
assert workflow["workflow"]["name"] == "E2E Test Workflow"
print(f"Workflow verified: {workflow['workflow']['name']}")

# Step 3: Stream some events
print("\nStreaming events...")
event_count = 0
for event in client.stream_session(logs_url):
    event_type = event.get("event") or event.get("type", "unknown")
    print(f"  [{event_type}]")
    event_count += 1
    if event_count >= 10:
        break
print(f"Received {event_count} events")

# Step 4: Send a message (if message_url available)
if message_url:
    print("\nSending message...")
    msg_result = client.send_message(message_url, "Click on the first link")
    print(f"Message sent: {msg_result}")

# Step 5: Close session
print("\nClosing session...")
close_result = client.close_session(session_id)
print(f"Close result: {close_result}")

print("\n=== E2E test complete ===")
```

## Test 7B: Full CLI flow

```bash
# Terminal 1: Start editor and stream
simplex editor --name "E2E CLI Test" --url "https://news.ycombinator.com" --json > /tmp/editor_output.jsonl &
EDITOR_PID=$!

# Wait for first line
sleep 45
head -1 /tmp/editor_output.jsonl | jq .

# Get session info
SESSION_ID=$(head -1 /tmp/editor_output.jsonl | jq -r '.session_id')
LOGS_URL=$(head -1 /tmp/editor_output.jsonl | jq -r '.logs_url')
echo "Session: $SESSION_ID"
echo "Logs: $LOGS_URL"

# Terminal 2: Connect to the same session
simplex connect "$LOGS_URL" --json | head -5

# Clean up
kill $EDITOR_PID
```

**Expected:** Both commands can stream from the same session.

## Test 7C: Multiple sessions concurrently

```python
from simplex import SimplexClient
import threading

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,
)

# Start two sessions
result1 = client.start_editor_session(name="Concurrent 1", url="https://example.com")
result2 = client.start_editor_session(name="Concurrent 2", url="https://example.org")

print(f"Session 1: {result1['session_id']}")
print(f"Session 2: {result2['session_id']}")

# Stream from both (briefly)
events1, events2 = [], []

def stream_events(logs_url, events_list, max_events=5):
    for event in client.stream_session(logs_url):
        events_list.append(event)
        if len(events_list) >= max_events:
            break

t1 = threading.Thread(target=stream_events, args=(result1["logs_url"], events1))
t2 = threading.Thread(target=stream_events, args=(result2["logs_url"], events2))
t1.start()
t2.start()
t1.join(timeout=60)
t2.join(timeout=60)

print(f"Session 1 events: {len(events1)}")
print(f"Session 2 events: {len(events2)}")

# Clean up
client.close_session(result1["session_id"])
client.close_session(result2["session_id"])
```

**Expected:** Both sessions run independently and can be streamed concurrently.
