# Simplex API & SSE Knowledgebase

> Comprehensive reference for the Simplex backend API surface, SSE streaming system, and SDK coverage gaps.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [API Endpoints (Non-Playground)](#2-api-endpoints-non-playground)
3. [SSE Streaming System](#3-sse-streaming-system)
4. [SDK Coverage Gap Analysis](#4-sdk-coverage-gap-analysis)
5. [CLI Opportunities](#5-cli-opportunities)

---

## 1. Authentication

### Two Auth Mechanisms

The API uses two completely separate auth mechanisms depending on the caller:

#### A. API Key Auth (`verify_api_key`) — for SDK/CLI consumers

- **Header**: `X-API-Key: <api_key>`
- **Validation**: PropelAuth `validate_api_key()` — validates the key and returns a `UserMetadata` object
- **Caching**: Results cached in Modal Dict `api-key-cache-new` for 24 hours
- **Access control**: Extracts `organization_id` from user to scope all queries
- **Usage tracking**: Logs to `api_usage` Supabase table
- **Full access check**: Verifies `full` flag on user — free users get limited sessions

#### B. Bearer Token Auth (`auth_token_validator`) — for dashboard/frontend

- **Header**: `Authorization: Bearer <token>`
- **Validation**: PropelAuth `validate_access_token_and_get_user()`
- **Caching**: Same pattern, `auth-token-cache` Modal Dict, 24h TTL
- **Used by**: Dashboard endpoints (`*_from_dashboard`, `start_editor`, playground)

#### C. In-Container Auth (SSE server inside `modal_browser.py`)

The SSE server running inside each browser container supports **both** auth methods:
- **Bearer token**: `Authorization: Bearer <token>` header, or `?token=<token>` query param (needed because EventSource doesn't support custom headers)
- **API key**: `X-API-Key: <key>` header, or `?api_key=<key>` query param
- Also validates organization membership against the container's `organization_id`

---

## 2. API Endpoints (Non-Playground)

### Base URL: `https://api.simplex.sh`

All endpoints below are on the main FastAPI app (`main.py`). Auth column indicates which auth mechanism is used:
- **API** = `verify_api_key` (X-API-Key header)
- **Token** = `auth_token_validator` (Bearer token)

---

### 2.1 Workflow Management

#### `GET /workflow/{workflow_id}` — Get Workflow Details
- **Auth**: API
- **Params**: `workflow_id` (path)
- **Response**:
  ```json
  {
    "succeeded": true,
    "workflow": {
      "id": "uuid",
      "name": "My Workflow",
      "actions": [...],
      "variables": {...},
      "url": "https://...",
      "metadata": "string or null"
    }
  }
  ```
- **Notes**: Also resolves prompt IDs inside `run_beta_agent` actions to full prompt objects. This is NOT in the SDK yet.

#### `POST /workflow` — Create Workflow
- **Auth**: API
- **Body** (JSON):
  ```json
  {
    "name": "string (required)",
    "url": "string (optional)",
    "actions": [{"function": "...", "params": {...}}],
    "variables": [{"name": "...", "type": "..."}],
    "structured_output": [{"name": "...", "type": "..."}],
    "metadata": "string (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "succeeded": true,
    "message": "Workflow created successfully",
    "workflow": { "id": "uuid", "name": "...", ... }
  }
  ```
- **Notes**: NOT in SDK yet. Critical for CLI workflow creation.

#### `PATCH /workflow/{workflow_id}` — Update Workflow (Partial)
- **Auth**: API
- **Body** (JSON): Any subset of workflow fields. Protected fields (`id`, `organization_id`, `created_at`, `user_id`) are stripped.
- **Response**:
  ```json
  {
    "succeeded": true,
    "message": "Workflow updated successfully",
    "workflow": { "id": "...", "name": "...", "actions": [...], "variables": {...}, "structured_output": [...], "url": "...", "metadata": "..." }
  }
  ```
- **Notes**: NOT in SDK. More powerful than `update_workflow_metadata` — can update name, actions, variables, etc.

#### `GET /search_workflows` — Search Workflows
- **Auth**: API
- **Query params**: `workflow_name` (optional), `metadata` (optional). If both omitted, returns ALL workflows for the org.
- **Response**:
  ```json
  {
    "succeeded": true,
    "workflows": [
      {
        "workflow_id": "uuid",
        "workflow_name": "...",
        "variables": {...},
        "metadata": "...",
        "url": "...",
        "created_at": "ISO timestamp"
      }
    ],
    "count": 5
  }
  ```
- **Notes**: Uses `ILIKE` for partial matching. Sorted by `created_at` descending.

#### `POST /workflow/duplicate/{workflow_id}` — Duplicate Workflow
- **Auth**: Token (dashboard only)
- **Notes**: Copies workflow + files from volume. Not relevant for SDK/CLI.

#### `POST /workflow/{workflow_id}/files/import` — Import Files to Workflow
- **Auth**: Token (dashboard only)
- **Notes**: File import from dashboard. Not relevant for SDK/CLI.

---

### 2.2 Workflow Execution

#### `POST /run_workflow` — Run a Workflow
- **Auth**: API
- **Content-Type**: `multipart/form-data` (NOT JSON!)
- **Form fields**:
  | Field | Type | Required | Notes |
  |---|---|---|---|
  | `workflow_id` | string | yes | |
  | `variables` | string (JSON) | no | JSON-encoded dict |
  | `metadata` | string | no | |
  | `webhook_url` | string | no | Overrides org-level webhook |
  | `files` | file upload(s) | no | Multiple files supported |
  | `use_editor_prompt` | bool | no | Uses editor prompt instead of production |
- **Response**:
  ```json
  {
    "succeeded": true,
    "message": "Workflow started",
    "session_id": "uuid",
    "vnc_url": "https://...",
    "logs_url": "https://...sse_tunnel.../stream"
  }
  ```
- **Internal flow**: Validates workflow exists → validates variables match schema → creates session in Supabase → spawns `ChromeContainer.run_chrome()` on Modal → returns session URLs
- **Key detail**: `logs_url` points to the in-container SSE server's `/stream` endpoint. This is the URL to connect to for live streaming.

#### `POST /run_workflow_from_dashboard` — Run Workflow (Dashboard)
- **Auth**: Token
- **Same as above** but without file uploads. Checks free session quota for non-full users.

#### `POST /start_editor` — Start Editor Session
- **Auth**: Token
- **Body** (JSON): `{ "workflow_id": "uuid" }`
- **Response**:
  ```json
  {
    "session_id": "uuid",
    "vnc_url": "https://...",
    "logs_url": "https://...sse_tunnel.../stream",
    "message_url": "https://...sse_tunnel.../message",
    "filesystem_url": "https://...sse_tunnel.../filesystem/events"
  }
  ```
- **Notes**: Starts a non-production session with `production=False`. Uses `test_data` from workflow as variables. Returns ALL URLs including `message_url` and `filesystem_url`. This is the key endpoint for interactive editing.

---

### 2.3 Session Management

#### `GET /session/{session_id}/status` — Get Session Status
- **Auth**: API
- **Response**:
  ```json
  {
    "in_progress": true,
    "success": null,
    "metadata": {},
    "workflow_metadata": {},
    "file_metadata": [],
    "scraper_outputs": [],
    "structured_output": null,
    "paused": false,
    "paused_key": ""
  }
  ```
- **Notes**: `in_progress` is `true` when status is `"Running"` or `"Shutting down"`. Data comes from `sessions.polling_info` in Supabase.

#### `POST /pause` — Pause a Session
- **Auth**: API
- **Form**: `session_id` (string)
- **Response**:
  ```json
  {
    "succeeded": true,
    "action": "pause",
    "pause_key": "..."
  }
  ```
- **Internal**: Sets `AGENT_PAUSED=true` env var in container, calls `agent_client.pause()`.

#### `POST /resume_session` — Resume a Session
- **Auth**: API
- **Form**: `session_id` (string)
- **Response**:
  ```json
  {
    "succeeded": true,
    "action": "resume_session",
    "pause_type": "external"
  }
  ```

#### `POST /interrupt` — Interrupt Agent
- **Auth**: API
- **Form**: `session_id` (string)
- **Notes**: Cancels current agent operation. NOT in SDK.

#### `POST /close_workflow_session` — Close a Workflow Session
- **Auth**: API
- **Form**: `session_id` (string)
- **Notes**: Gracefully closes a running session. NOT in SDK.

#### `POST /close_session_from_dashboard` — Close Session (Dashboard)
- **Auth**: Token
- **Notes**: Dashboard variant.

---

### 2.4 Session Data Retrieval

#### `GET /download_session_files` — Download Session Files
- **Auth**: API
- **Query params**: `session_id` (required), `filename` (optional)
- **Response**: Binary file data (zip if no filename specified, raw file otherwise)

#### `GET /retrieve_session_replay/{session_id}` — Get Replay Video
- **Auth**: API
- **Response**: Binary MP4 data
- **Notes**: Fetches from S3 `{session_id}/session_recording.mp4`

#### `GET /retrieve_session_logs/{session_id}` — Get Session Logs
- **Auth**: API
- **Response**: JSON `{ "logs": [...] }`
- **Notes**: Fetches from S3 `{session_id}/logs_final.json`. Returns `null` logs if still running.

#### `GET /get_session_logs/{session_id}` — Get Session Logs (v2)
- **Auth**: API
- **Response**: Full session log data with metadata
- **Notes**: Different format from `retrieve_session_logs`. Also NOT in SDK.

#### `GET /get_session_logs_new/{session_id}` — Get Session Logs (v3)
- **Auth**: API
- **Notes**: Newer log format. NOT in SDK.

#### `GET /retrieve_generated_code/{session_id}` — Get Generated Code
- **Auth**: API
- **Response**: `{ "succeeded": true, "code": "..." }`
- **Notes**: Returns workflow code generated during session. NOT in SDK.

---

### 2.5 Workflow Files (Volume)

#### `GET /workflow_files/{workflow_id}` — Get Workflow File Tree
- **Auth**: Token
- **Response**: `{ "succeeded": true, "files": [...nested FileNode tree...] }`
- **Notes**: Reads from Modal volume `workflow-scripts`. NOT in SDK.

#### `GET /workflow_files/{workflow_id}/content` — Get Workflow File Content
- **Auth**: Token
- **Query**: `path` (required) — relative path within workflow
- **Response**: `{ "succeeded": true, "content": "...", "language": "python" }`
- **Notes**: Returns file content with language detection. NOT in SDK.

#### `GET /session_files/{session_id}` — Get Session File Tree
- **Auth**: Token
- **Notes**: Similar to workflow_files but for session data.

#### `GET /session_files/{session_id}/content` — Get Session File Content
- **Auth**: Token
- **Notes**: Similar to workflow file content.

---

### 2.6 Prompts

#### `POST /prompt` — Create a Prompt
- **Auth**: API
- **Body** (JSON):
  ```json
  {
    "prompt": "string (required)",
    "name": "string (optional, auto-generated if omitted)"
  }
  ```
- **Response**:
  ```json
  {
    "succeeded": true,
    "message": "Prompt created successfully",
    "prompt_id": "uuid"
  }
  ```
- **Notes**: NOT in SDK. Prompts are used in workflow actions (`run_beta_agent` → `prompts` param).

---

### 2.7 Custom Tools

#### `POST /create_custom_tool` — Create Custom Tool
- **Auth**: API
- **Body** (JSON):
  ```json
  {
    "name": "string (required, unique per org)",
    "description": "string (required, for LLM)",
    "javascript_code": "string (required)",
    "parameters_schema": [{"name": "...", "type": "...", "description": "..."}]
  }
  ```
- **Response**: `{ "succeeded": true, "tool": {...} }`

#### `GET /get_custom_tools` — List Custom Tools
- **Auth**: API
- **Response**: `{ "succeeded": true, "tools": [...] }`

#### `DELETE /delete_custom_tool/{name}` — Delete Custom Tool
- **Auth**: API
- **Response**: `{ "succeeded": true }`

#### `PUT /update_custom_tool/{name}` — Update Custom Tool
- **Auth**: API
- **Body**: Same as create (partial updates supported)
- **Response**: `{ "succeeded": true, "tool": {...} }`

---

### 2.8 Share Links & Video

#### `GET /generate_share_link` — Generate Share Link
- **Auth**: Token
- **Query**: `session_id`
- **Response**: `{ "succeeded": true, "share_link": "https://simplex.sh/share/..." }`

#### `GET /get_session_video/{session_id}` — Get Session Video URL
- **Auth**: Token
- **Response**: `{ "succeeded": true, "video_url": "presigned S3 URL" }`

#### Various `*_from_link` endpoints — Public access via share codes
- No auth required, uses unique code from share link

---

### 2.9 2FA & Network

#### `POST /generate_2fa_regex` — Generate 2FA regex pattern
- **Auth**: API
- **Body**: `{ "screenshot": "base64...", "context": "..." }`

#### `POST /add_2fa_config` — Add 2FA configuration
- **Auth**: API
- **Body**: `{ "workflow_id": "...", "regex": "...", ... }`

#### `POST /get_graphql_auth` / `POST /get_network_response` — Network inspection
- **Auth**: Token (dashboard)

---

### 2.10 Session Store

#### `GET /get_session_store/{session_id}` — Get Session Store Data
- **Auth**: API
- **Response**: Browser session cookies/localStorage for session reuse

#### `GET /get_session_store` — Get Session Store (API)
- **Auth**: API
- **Query**: `session_id`

---

### 2.11 Metadata Update (Legacy)

#### `POST /update_workflow_metadata` (in `_http_client.py` SDK)
- This endpoint is NOT visible in the main.py grep — it may be handled by the `PATCH /workflow/{workflow_id}` endpoint now, or it may be a legacy alias. The SDK's `update_workflow_metadata` method POSTs form data to `/update_workflow_metadata`.

---

## 3. SSE Streaming System

### Architecture Overview

Each browser session runs a **Chrome container** on Modal. Inside each container, a FastAPI server runs on port **7777** and is exposed via `modal.forward()` as an HTTPS tunnel. This gives each session its own unique SSE server URL.

```
Client (CLI/Browser)
    |
    | HTTPS (modal.forward tunnel)
    v
Container SSE Server (port 7777, FastAPI + uvicorn)
    |
    ├── GET  /stream          → SSE event stream (agent activity)
    ├── GET  /health          → Health check
    ├── POST /message         → Send message to running agent
    ├── GET  /filesystem/events → SSE filesystem change stream
    ├── GET  /filesystem/tree   → Full file tree snapshot
    ├── GET  /filesystem/read   → Read file content
    └── POST /filesystem/write  → Write file content
```

### 3.1 URL Discovery

When a session starts, the URLs are stored in a **Modal Dict** named `session-dict-{session_id}`:

| Key | Value | Example |
|---|---|---|
| `vnc_url` | Full noVNC URL | `https://host:port/vnc_minimal.html?...` |
| `logs_url` | SSE stream URL | `https://{sse_tunnel.host}:{sse_tunnel.port}/stream` |
| `message_url` | Message POST URL | `https://{sse_tunnel.host}:{sse_tunnel.port}/message` |
| `filesystem_url` | Filesystem SSE URL | `https://{sse_tunnel.host}:{sse_tunnel.port}/filesystem/events` |
| `connect_url` | WebSocket debug URL | `wss://...` |
| `session_id` | Session ID | `uuid` |
| `timezone` | Container timezone | `America/Los_Angeles` |

The `logs_url` and `message_url` are also returned directly in `/run_workflow` and `/start_editor` responses.

### 3.2 GET /stream — Agent Activity SSE Stream

**This is the primary endpoint for streaming agent logs and activity.**

#### Connection
```
GET https://{sse_host}:{sse_port}/stream
Authorization: Bearer <token>
# OR
X-API-Key: <api_key>
# OR (for EventSource which can't set headers)
GET /stream?token=<bearer_token>
GET /stream?api_key=<api_key>
```

#### SSE Wire Format
```
data: {"event": "RunStarted", "content": "", "content_type": "text", "session_id": "...", "agent_id": "browser-agent", "run_id": "uuid", "created_at": 1234567890}\n\n

data: {"event": "RunContent", "content": "I'll navigate to the login page", "content_type": "text", "session_id": "...", "agent_id": "browser-agent", "created_at": 1234567891}\n\n

: keep-alive\n\n
```

Each message is `data: {JSON}\n\n`. Keep-alive comments (`: keep-alive\n\n`) are sent every ~1 second when idle.

#### Event Types (RunEvent class)

| Event | Description | Key Fields |
|---|---|---|
| `RunStarted` | Agent run initialized | `content`, `session_id`, `agent_id`, `run_id`, `created_at` |
| `RunContent` | Agent text output / thinking | `content`, `content_type` ("text"), `session_id`, `agent_id`, `created_at` |
| `ToolCallStarted` | Tool execution beginning | `tool` (object with `tool_call_id`, `tool_name`, `tool_args`, `role`, `isInSubagent`), `content_type` ("tool") |
| `ToolCallCompleted` | Tool execution finished | `tool` (same shape + `content` with result), `content_type` ("tool") |
| `ToolRejected` | Tool call blocked by hooks | Similar to ToolCallCompleted |
| `RunCompleted` | Agent run finished | `content`, `session_id`, `agent_id` |
| `RunError` | Agent encountered error | `content` (error message), `session_id`, `agent_id` |
| `AgentRunning` | Agent processing state change | `content` (bool string), `session_id`, `agent_id` |
| `NewMessage` | Message boundary marker | `content_type` ("message_boundary") — separates distinct agent messages |

#### Flow Events (FlowEvent class)

| Event | Description | Key Fields |
|---|---|---|
| `FlowPaused` | Workflow paused at a pause step | `pause_key`, `pause_id`, `session_id`, `created_at` |
| `FlowResumed` | Workflow resumed from pause | `pause_key`, `pause_id`, `session_id`, `created_at` |

#### ToolCallStarted `tool` Object Shape
```json
{
  "role": "assistant",
  "content": null,
  "tool_call_id": "toolu_abc123",
  "tool_name": "computer",
  "tool_args": { "action": "click", "coordinate": [100, 200] },
  "tool_call_error": false,
  "created_at": 1234567892,
  "isInSubagent": false
}
```

#### ToolCallCompleted `tool` Object Shape
```json
{
  "role": "tool",
  "content": "Screenshot captured successfully",
  "tool_call_id": "toolu_abc123",
  "tool_name": "computer",
  "tool_args": {},
  "tool_call_error": false,
  "created_at": 1234567893,
  "isInSubagent": false
}
```

#### Subscriber Model
- Uses **fan-out via shared history array** — NOT a queue per subscriber
- On connect: all historical messages are replayed first, then live messages stream
- Multiple simultaneous subscribers supported (each tracks its own read index)
- Keep-alive every ~1 second during idle periods

### 3.3 POST /message — Send Message to Agent

**This is how you send prompts/commands to a running session.**

#### Request
```
POST https://{sse_host}:{sse_port}/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Navigate to the settings page and click on Account"
}
```

#### Response
```json
{"status": "received"}
```

#### Special Commands

**Cancel a queued message:**
```json
{
  "message": "SIMPLEX_CANCEL <original_message_content>"
}
```
Response: `{"status": "cancelled", "cancelled_count": 1}` or `{"status": "not_found", "cancelled_count": 0}`

**Resume a paused flow:**
```json
{
  "flow_resume": "pause_key_value"
}
```
Response: `{"status": "resumed", "pause_type": "external"|"internal", "key": "..."}` or `{"status": "error", "message": "..."}`

#### Message Flow
1. Message received at POST /message
2. Put into `client_messages_queue` (asyncio.Queue)
3. Agent's `agent_client` picks up the message from the queue
4. Agent processes the message and emits SSE events to `/stream`

### 3.4 GET /filesystem/events — Filesystem SSE Stream

Streams filesystem changes in the container's `/home/chrome_user/agent` directory.

#### Event Format
```
data: {"type": "FILE_CREATED", "path": "/data/output.json", "name": "output.json"}\n\n
data: {"type": "FILE_MODIFIED", "path": "/flow.py", "name": "flow.py"}\n\n
data: {"type": "SHARED_STATE_MODIFIED", "data": {"flow_pause_active": true, ...}}\n\n
```

#### Event Types
- `FILE_CREATED`, `FILE_MODIFIED`, `FILE_DELETED`
- `DIR_CREATED`, `DIR_DELETED`
- `FILE_MOVED`, `DIR_MOVED` (with `oldPath` and `newPath`)
- `SHARED_STATE_MODIFIED` — internal agent state changes
- `FULL_SYNC` — complete file tree snapshot

### 3.5 Other Container Endpoints

#### `GET /filesystem/tree` — Get Full File Tree
- **Auth**: Token only
- **Response**: `{"type": "FULL_SYNC", "files": [...], "watchPath": "/home/chrome_user/agent"}`

#### `GET /filesystem/read` — Read File from Container
- **Auth**: Token only
- **Query**: `path` — relative path within watch directory
- **Response**: Binary file content with appropriate MIME type

#### `POST /filesystem/write` — Write File to Container
- **Auth**: Token only
- **Body**: `{"path": "flow.py", "content": "...", "create": true}`
- **Response**: `{"path": "/flow.py", "name": "flow.py", "succeeded": true}`
- **Notes**: If writing `data/variables.json`, auto-syncs to `new_workflows.test_data` in Supabase

---

## 4. SDK Coverage Gap Analysis

### Currently in SDK

| SDK Method | API Endpoint | HTTP Method |
|---|---|---|
| `run_workflow()` | `/run_workflow` | POST (form) |
| `get_session_status()` | `/session/{id}/status` | GET |
| `download_session_files()` | `/download_session_files` | GET |
| `retrieve_session_replay()` | `/retrieve_session_replay/{id}` | GET |
| `retrieve_session_logs()` | `/retrieve_session_logs/{id}` | GET |
| `pause()` | `/pause` | POST (form) |
| `resume()` | `/resume_session` | POST (form) |
| `search_workflows()` | `/search_workflows` | GET |
| `update_workflow_metadata()` | `/update_workflow_metadata` | POST (form) |

### NOT in SDK (API-key authenticated, suitable for CLI)

| Endpoint | Method | Priority | Notes |
|---|---|---|---|
| `GET /workflow/{id}` | GET | **HIGH** | Get full workflow details |
| `POST /workflow` | POST (JSON) | **HIGH** | Create new workflow |
| `PATCH /workflow/{id}` | PATCH (JSON) | **HIGH** | Update workflow (any fields) |
| `POST /interrupt` | POST (form) | **MEDIUM** | Interrupt running agent |
| `POST /close_workflow_session` | POST (form) | **MEDIUM** | Close/cancel session |
| `POST /prompt` | POST (JSON) | **MEDIUM** | Create reusable prompt |
| `POST /create_custom_tool` | POST (JSON) | **MEDIUM** | Create custom JS tool |
| `GET /get_custom_tools` | GET | **MEDIUM** | List custom tools |
| `PUT /update_custom_tool/{name}` | PUT (JSON) | **LOW** | Update custom tool |
| `DELETE /delete_custom_tool/{name}` | DELETE | **LOW** | Delete custom tool |
| `GET /get_session_store/{id}` | GET | **LOW** | Get session cookies/storage |
| `GET /retrieve_generated_code/{id}` | GET | **LOW** | Get generated code |

### NOT in SDK (Token-only, requires dashboard auth)

These endpoints use Bearer token auth and are NOT accessible via API key:

| Endpoint | Notes |
|---|---|
| `POST /start_editor` | **CRITICAL for CLI connect feature** — but needs Token auth |
| `GET /workflow_files/{id}` | File tree from volume |
| `GET /workflow_files/{id}/content` | File content from volume |
| `POST /workflow/duplicate/{id}` | Duplicate workflow |
| All `*_from_dashboard` variants | Dashboard-only versions |

---

## 5. CLI Opportunities

### 5.1 New Commands to Add

Based on the gap analysis:

```
simplex workflow get <id>          → GET /workflow/{id}
simplex workflow create            → POST /workflow
simplex workflow update <id>       → PATCH /workflow/{id}
simplex interrupt <session_id>     → POST /interrupt
simplex close <session_id>         → POST /close_workflow_session
simplex prompt create              → POST /prompt
simplex tools list                 → GET /get_custom_tools
simplex tools create               → POST /create_custom_tool
simplex tools delete <name>        → DELETE /delete_custom_tool/{name}
```

### 5.2 The Big Feature: `simplex connect <session_id>`

The killer CLI feature is connecting to a live session's SSE stream. This enables:

1. **Stream logs** from a running session in real-time
2. **Send messages** to the agent (prompts, instructions)
3. **Resume paused flows** from the terminal
4. **Pipe to AI agents** like Claude Code for autonomous workflow building

#### Implementation Plan

```
simplex connect <session_id>
  --stream-only    # Just stream logs, no input
  --json           # Output raw JSON events instead of formatted
```

**Step 1**: Resolve session URLs
- Read `logs_url` and `message_url` from Modal Dict `session-dict-{session_id}`
- OR: get them from the `/run_workflow` or `/start_editor` response

**Step 2**: Connect to SSE stream
- Open HTTP connection to `{logs_url}` with `X-API-Key` header (or `?api_key=` query param)
- Parse `data: {JSON}\n\n` lines
- Display formatted events in terminal (Rich live display)

**Step 3**: Accept input
- Read from stdin or provide a prompt
- POST to `{message_url}` with `{"message": "user input"}`
- Continue streaming response

#### Auth Challenge

The SSE server inside containers supports API key auth via `X-API-Key` header or `?api_key=` query param. This means **CLI users can authenticate with their existing API key** — no Bearer token needed.

However, `POST /start_editor` (which creates editor sessions with `message_url`) currently requires Bearer token auth. Options:
1. Add API key auth to `/start_editor` (backend change)
2. Use `POST /run_workflow` with `use_editor_prompt=true` (already API key auth)
3. Add a new API-key-authenticated endpoint for creating interactive sessions

#### URL Resolution

The `logs_url` and `message_url` are stored in Modal Dict `session-dict-{session_id}`. The SDK needs a way to fetch these. Options:
1. Add `GET /session/{id}/urls` endpoint to main.py that reads from session dict
2. Return `message_url` in `run_workflow` response (currently only returns `logs_url`)
3. Have the CLI derive `message_url` from `logs_url` (same host, just different path)

**Easiest approach**: Since `logs_url` is `https://{host}:{port}/stream`, the `message_url` is always `https://{host}:{port}/message` on the same host. The CLI can derive it.

### 5.3 SDK Methods Needed

New SDK methods to add for CLI support:

```python
# Workflow CRUD
client.get_workflow(workflow_id) -> dict
client.create_workflow(name, url=None, actions=None, variables=None, ...) -> dict
client.update_workflow(workflow_id, **fields) -> dict

# Session control
client.interrupt(session_id) -> dict
client.close_session(session_id) -> dict

# Prompts
client.create_prompt(prompt, name=None) -> dict

# Custom tools
client.list_custom_tools() -> dict
client.create_custom_tool(name, description, javascript_code, ...) -> dict
client.delete_custom_tool(name) -> dict
client.update_custom_tool(name, **fields) -> dict

# SSE Streaming (new pattern — not typical SDK request/response)
client.connect_stream(logs_url) -> Iterator[dict]  # yields SSE events
client.send_message(message_url, message) -> dict
```
