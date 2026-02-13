# Test 08: Error Handling

## Setup

```python
from simplex import SimplexClient, SimplexError, WorkflowError, AuthenticationError

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
)
```

## Test 8A: Invalid API key

```python
bad_client = SimplexClient(
    api_key="invalid-key-12345",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
)

try:
    bad_client.start_editor_session(name="Bad Key", url="https://example.com")
    assert False, "Should have raised"
except AuthenticationError as e:
    print(f"Expected auth error: {e}")
except WorkflowError as e:
    print(f"Workflow error (also acceptable): {e}")
```

**Expected:** Raises AuthenticationError or WorkflowError with 401.

## Test 8B: Invalid API key on CLI

```bash
SIMPLEX_API_KEY="bad-key" simplex editor --name "Bad" --url "https://example.com"
```

**Expected:** Error message about invalid API key.

## Test 8C: No API key configured

```bash
unset SIMPLEX_API_KEY
# Make sure no credentials file exists
mv ~/.simplex/credentials ~/.simplex/credentials.bak 2>/dev/null

simplex editor --name "No Key" --url "https://example.com"
```

**Expected:** Error: "Not authenticated. Run 'simplex login' or set SIMPLEX_API_KEY."

```bash
# Restore credentials
mv ~/.simplex/credentials.bak ~/.simplex/credentials 2>/dev/null
```

## Test 8D: Empty API key

```python
try:
    client = SimplexClient(api_key="")
    assert False, "Should have raised"
except ValueError as e:
    print(f"Expected: {e}")
```

**Expected:** Raises `ValueError: api_key is required`.

## Test 8E: stream_session with bad URL

```python
try:
    for event in client.stream_session("https://nonexistent.invalid/stream"):
        pass
except Exception as e:
    print(f"Expected error: {type(e).__name__}: {e}")
```

**Expected:** Raises a connection error (NetworkError or requests exception).

## Test 8F: send_message with bad URL

```python
try:
    client.send_message("https://nonexistent.invalid/message", "test")
except Exception as e:
    print(f"Expected error: {type(e).__name__}: {e}")
```

**Expected:** Raises a connection error.

## Test 8G: close_session with invalid session_id

```python
try:
    client.close_session("00000000-0000-0000-0000-000000000000")
except WorkflowError as e:
    print(f"Expected error: {e}")
```

**Expected:** Raises WorkflowError (session not found or already closed).

## Test 8H: start_editor_session timeout handling

```python
# The start_editor_session endpoint can take 30-40 seconds.
# With default 30s timeout, it might time out.
# Use a longer timeout for this endpoint.

client_short = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=5,  # Very short
)

try:
    client_short.start_editor_session(name="Timeout Test", url="https://example.com")
    print("Completed (shouldn't happen with 5s timeout)")
except Exception as e:
    print(f"Expected timeout: {type(e).__name__}: {e}")
```

**Expected:** Times out since session creation takes ~30-40s.
