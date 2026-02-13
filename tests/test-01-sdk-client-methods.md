# Test 01: SDK Client Methods

## Setup

```bash
export SIMPLEX_API_KEY="your-api-key-here"
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
```

## Test 1A: create_workflow

```python
from simplex import SimplexClient

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
)

result = client.create_workflow(
    name="SDK Test Workflow",
    url="https://example.com",
)
print(result)
# Expected: dict with workflow_id, name, etc.
workflow_id = result["workflow"]["id"]
print(f"Created workflow: {workflow_id}")
```

**Expected:** Returns a workflow object with an ID.

## Test 1B: get_workflow

```python
result = client.get_workflow(workflow_id)
print(result)
# Response is: {"succeeded": true, "workflow": {"id": "...", "name": "...", ...}}
print(f"Name: {result['workflow']['name']}")
# Expected: Full workflow object with name="SDK Test Workflow", url="https://example.com"
```

**Expected:** Returns the workflow we just created.

## Test 1C: update_workflow

```python
result = client.update_workflow(workflow_id, name="Updated Workflow Name")
print(result)
```

**Expected:** Returns updated workflow with new name.

## Test 1D: start_editor_session

```python
result = client.start_editor_session(
    name="Editor Test",
    url="https://example.com",
)
print(result)
# Expected keys: succeeded, workflow_id, session_id, vnc_url, logs_url, message_url, filesystem_url
assert result["succeeded"] is True
assert result["session_id"]
assert result["workflow_id"]
assert result["vnc_url"]
assert result["logs_url"]
print(f"Session: {result['session_id']}")
print(f"VNC: {result['vnc_url']}")
```

**Expected:** Returns succeeded=True with all URLs populated. This will take ~30-40s.

## Test 1E: start_editor_session with test_data

```python
result = client.start_editor_session(
    name="Editor With Vars",
    url="https://example.com",
    test_data={"username": "test_user", "email": "test@example.com"},
)
print(result)
assert result["succeeded"] is True
```

**Expected:** Same as 1D, but the session has access to the test_data variables.

## Test 1F: stream_session

```python
# Use logs_url from Test 1D or 1E
logs_url = result["logs_url"]
for event in client.stream_session(logs_url):
    print(event)
    # Break after a few events for testing
    break
```

**Expected:** Yields SSE event dicts with a "type" field.

## Test 1G: send_message

```python
message_url = result["message_url"]
if message_url:
    response = client.send_message(message_url, "Hello from SDK test!")
    print(response)
```

**Expected:** Returns a response confirming the message was received.

## Test 1H: close_session

```python
session_id = result["session_id"]
response = client.close_session(session_id)
print(response)
```

**Expected:** Session closes gracefully.

## Test 1I: search_workflows

```python
results = client.search_workflows(workflow_name="Editor Test")
print(results)
assert results["succeeded"]
assert len(results["workflows"]) > 0
```

**Expected:** Finds the workflows created in previous tests.
