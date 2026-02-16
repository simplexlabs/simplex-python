# Test 04: Base URL Configuration

## Overview

The SDK and CLI can be pointed at different environments using:
1. **SDK:** `base_url` parameter in `SimplexClient()`
2. **CLI:** `SIMPLEX_BASE_URL` environment variable

## Test 4A: SDK with custom base_url

```python
from simplex import SimplexClient

# Dev environment
client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
)

# Verify it works
result = client.search_workflows(workflow_name="test")
print(result)
```

**Expected:** Requests go to the dev environment URL.

## Test 4B: SDK default base_url

```python
from simplex import SimplexClient

client = SimplexClient(api_key="YOUR_KEY")
print(client._http_client.base_url)
# Expected: "https://api.simplex.sh"
```

**Expected:** Default is `https://api.simplex.sh`.

## Test 4C: CLI with SIMPLEX_BASE_URL env var

```bash
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
export SIMPLEX_API_KEY="YOUR_KEY"

simplex editor --name "Dev Test" --url "https://example.com"
```

**Expected:** The CLI uses the dev environment backend.

## Test 4D: CLI without SIMPLEX_BASE_URL (production default)

```bash
unset SIMPLEX_BASE_URL
export SIMPLEX_API_KEY="YOUR_KEY"

simplex editor --name "Prod Test" --url "https://example.com"
```

**Expected:** CLI uses the default production URL (`https://api.simplex.sh`).

## Test 4E: All CLI commands respect SIMPLEX_BASE_URL

The following commands should all use the dev environment when `SIMPLEX_BASE_URL` is set:

```bash
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"

# Run
simplex run <workflow_id>

# Session status
simplex sessions status <session_id>

# Session logs
simplex sessions logs <session_id>

# Workflows list
simplex workflows list --name "test"

# Editor
simplex editor --name "Test" --url "https://example.com"

# Connect
simplex connect <session_id_or_url>
```

## Test 4F: SDK timeout with custom base_url

```python
client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
    timeout=120,  # Longer timeout for dev/slow endpoints
)
result = client.start_editor_session(name="Timeout Test", url="https://example.com")
print(result)
```

**Expected:** Works with increased timeout. `start_editor_session` can take 30-40s.
