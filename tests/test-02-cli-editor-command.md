# Test 02: CLI `simplex editor` Command

## Setup

```bash
export SIMPLEX_API_KEY="your-api-key-here"
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
```

## Test 2A: Basic editor session

```bash
simplex editor --name "CLI Editor Test" --url "https://example.com"
```

**Expected output:**
```
Workflow ID  <uuid>
Session ID   <uuid>
VNC URL      https://...
Logs URL     https://...
Message URL  https://...

Streaming events... (Ctrl+C to stop)

[events stream here]
```

**Verify:**
- Workflow ID and Session ID are printed
- VNC URL is a valid URL (you can open it in browser to see the browser)
- Events start streaming after session boot (~30-40s)
- Ctrl+C cleanly exits with "Disconnected."

## Test 2B: Editor with variables

```bash
simplex editor --name "Var Test" --url "https://example.com" --var username=testuser --var email=test@test.com
```

**Expected:** Same as 2A, but the session has access to `username` and `email` variables.

## Test 2C: Editor with JSON output

```bash
simplex editor --name "JSON Test" --url "https://example.com" --json
```

**Expected output:**
```json
{"type": "SessionStarted", "session_id": "...", "workflow_id": "...", "vnc_url": "...", "logs_url": "...", "message_url": "..."}
{"type": "RunContent", "content": "..."}
...
```

Each line is a valid JSON object. First line is `SessionStarted` with session metadata, followed by SSE events.

**Verify:**
- Output is valid JSONL (one JSON per line)
- Can pipe to `jq` for filtering: `simplex editor --name "Test" --url "https://example.com" --json | jq '.type'`

## Test 2D: Short flag aliases

```bash
simplex editor -n "Alias Test" -u "https://example.com" -v key=value
```

**Expected:** Same as 2A. `-n`, `-u`, `-v` are aliases for `--name`, `--url`, `--var`.

## Test 2E: Missing required params

```bash
simplex editor --name "No URL"
```

**Expected:** Error — `--url` is required.

```bash
simplex editor --url "https://example.com"
```

**Expected:** Error — `--name` is required.

## Test 2F: Invalid variable format

```bash
simplex editor --name "Bad Var" --url "https://example.com" --var "no-equals-sign"
```

**Expected:** Error message: `Invalid variable format: 'no-equals-sign'. Use key=value.`

## Test 2G: Help text

```bash
simplex editor --help
```

**Expected:**
```
Usage: simplex editor [OPTIONS]

  Create a workflow and start an editor session, then stream events.

Options:
  -n, --name TEXT        Workflow name [required]
  -u, --url TEXT         Starting URL [required]
  -v, --var TEXT         Test data variable as key=value (repeatable)
  --json                 Output raw JSON events (for piping)
  --help                 Show this message and exit.
```
