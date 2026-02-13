# Test 03: CLI `simplex connect` Command

## Setup

```bash
export SIMPLEX_API_KEY="your-api-key-here"
export SIMPLEX_BASE_URL="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run"
```

First, start an editor session to get a session_id and logs_url:
```bash
simplex editor --name "Connect Source" --url "https://example.com" --json | head -1
# Copy session_id and logs_url from the output
```

## Test 3A: Connect by logs_url

```bash
simplex connect "https://<host>:<port>/stream"
```

**Expected:**
```
Logs URL     https://<host>:<port>/stream
Message URL  https://<host>:<port>/message

Streaming events... (Ctrl+C to stop)

[events stream here]
```

**Verify:**
- Message URL is auto-derived from logs_url (replacing `/stream` with `/message`)
- Events stream in real time
- Ctrl+C exits cleanly

## Test 3B: Connect with JSON output

```bash
simplex connect "https://<host>:<port>/stream" --json
```

**Expected:** Raw JSONL output, one event per line. No Rich formatting.

**Verify:**
- Each line is valid JSON
- Can pipe to `jq`: `simplex connect <url> --json | jq '.type'`

## Test 3C: Connect to non-existent URL

```bash
simplex connect "https://nonexistent.example.com/stream"
```

**Expected:** Error message about stream/connection failure.

## Test 3D: Connect by session_id (if session status endpoint returns logs_url)

```bash
simplex connect <session_id>
```

**Expected:** Looks up the session, gets logs_url, and starts streaming. If the session status endpoint doesn't return logs_url, it should show an error like "No logs_url found for session <id>".

## Test 3E: Help text

```bash
simplex connect --help
```

**Expected:**
```
Usage: simplex connect [OPTIONS] SESSION_ID

  Stream live events from a running session.

Options:
  --json  Output raw JSON events (for piping)
  --help  Show this message and exit.
```

## Test 3F: Piping JSON output to another tool

```bash
# Count event types
simplex connect <logs_url> --json | jq -r '.type' | sort | uniq -c

# Filter only content events
simplex connect <logs_url> --json | jq 'select(.type == "RunContent") | .content'

# Save to file
simplex connect <logs_url> --json > session_events.jsonl
```

**Expected:** JSON output is clean enough to pipe through standard tools.
