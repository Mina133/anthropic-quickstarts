# Computer Use Agent (FastAPI)

A FastAPI backend that reuses Anthropic computer-use agent stack (from `anthropic-quickstarts/computer-use-demo`) and replaces the experimental Streamlit UI with REST/WebSocket APIs, database persistence, and a minimal HTML/JS frontend. Includes Docker and docker-compose for local development and deployment.

## Features

- **FastAPI backend with CORS**
- **SQLite (default) or Postgres** via `DATABASE_URL` with SQLAlchemy ORM
- **WebSocket** `/sessions/{id}/stream` for real-time updates
- **Sessions and messages persistence**
- **Optional MongoDB event store** for historical event replay
- **Per-session “VM” container** via Docker, exposing dynamic noVNC/VNC ports
- **Minimal frontend** (static HTML/JS) served by nginx container
- **Dockerfile and docker-compose**

## Architecture overview

The backend exposes synchronous REST endpoints for session and message management, plus a WebSocket stream for live agent/tool events. A background agent loop is triggered on user messages, streaming incremental output and tool results to connected clients. Optionally, events are also persisted to MongoDB for later retrieval.

```
Client ──REST──▶ FastAPI (app/) ──SQLAlchemy──▶ DB (SQLite/Postgres)
   │                     │
   │                     ├─WebSocket broadcast◀── StreamManager
   │                     │
   │                     ├─AgentRunner ──▶ Anthropic model + computer-use tools
   │                     │
   │                     └─VMManager ──▶ Docker noVNC/VNC container per session
```

## App structure and responsibilities

```
app/
  __init__.py             # package init
  config.py               # Pydantic settings (env-driven)
  database.py             # SQLAlchemy engine, Base, session dependency
  main.py                 # FastAPI app factory, CORS, router wiring, /healthz
  schemas.py              # Pydantic request/response models
  models/
    session.py            # Session ORM model
    message.py            # Message ORM model
  routers/
    sessions.py           # Session CRUD, archive, events, fetch with history
    messages.py           # Post user message + background agent run
    stream.py             # WebSocket endpoint per session
    vnc.py                # (Deprecated) global VNC info
  services/
    agent_runner.py       # Orchestrates agent turn and event streaming
    stream_manager.py     # Manages WS connections and broadcasts
    event_store.py        # Optional MongoDB-backed event persistence
    vm_manager.py         # Docker container lifecycle for noVNC/VNC
```

### Configuration (`app/config.py`)

Settings are loaded from environment variables and `.env` (via Pydantic BaseSettings):

- **Core**: `app_name`, `environment`
- **Networking**: `api_host`, `api_port`, `frontend_origin`
- **Database**: `database_url` (default `sqlite:///./data/app.db`)
- **Anthropic**: `anthropic_api_key`, `anthropic_model` (default `claude-3-7-sonnet-20250219`), `enable_computer_use`
- **VNC/Media**: `vnc_host`, `vnc_port`, `novnc_port`, `vnc_password`, `media_dir`
- **MongoDB (optional)**: `mongodb_uri`, `mongodb_db`

Access via `get_settings()` which is memoized.

### Database (`app/database.py`)

- Creates SQLAlchemy `engine` and `SessionLocal` from `database_url`. Uses `check_same_thread=False` when SQLite.
- Exposes `Base = declarative_base()` and `get_db()` FastAPI dependency.

### Models (`app/models/*.py`)

- **Session**
  - `id` (UUID string), `title`, `status`, `created_at`, `updated_at`, `archived`
  - `last_agent_state` (JSON), `metadata_json` (JSON, contains VM info)
- **Message**
  - `id` (UUID string), `session_id` (FK), `role` (`user`/`assistant`/`system`/`tool`)
  - `content` (text), `content_json` (JSON, used for structured assistant content), `created_at`

### Schemas (`app/schemas.py`)

- Request: `SessionCreate`, `MessageCreate`
- Response: `SessionRead`, `MessageRead`, `ChatHistoryRead` (session + messages)

### HTTP + WebSocket routers (`app/routers/*.py`)

- **POST `/sessions`** → Create a session
  - Body: `{ "title"?: string, "metadata"?: object }`
  - Side effect: `vm_manager.create_vm()` stores `{container_id, novnc_port, vnc_port}` in `session.metadata_json.vm`
  - Returns: `SessionRead`

- **GET `/sessions`** → List sessions (newest first)
  - Returns: `SessionRead[]`

- **GET `/sessions/{id}`** → Session with history
  - Returns: `ChatHistoryRead` `{ session, messages }`

- **POST `/sessions/{id}/archive`** → Archive + stop VM
  - Attempts `vm_manager.stop_vm(container_id)` if present in metadata
  - Returns: updated `SessionRead`

- **GET `/sessions/{id}/events`** → Historical events (if MongoDB configured)
  - Returns: `[{ type, at, ... }]` from `event_store`

- **POST `/sessions/{id}/messages`** → Send user message
  - Body: `{ "role"?: "user"|"system" (default user), "content": string }`
  - Persists user message, emits `user_message` event, schedules background agent run
  - Returns: `MessageRead` for the user message

- **WS `/sessions/{id}/stream`** → Real-time events
  - Server broadcasts as the agent runs; client reads JSON messages until closed

- **GET `/vnc/info`** (deprecated)
  - Global/fallback VNC info from static settings; prefer per-session ports in `session.metadata_json.vm`

### Event streaming and types

Events are JSON objects broadcast over the WebSocket and optionally appended to MongoDB via `event_store`:

- `{ "type": "user_message", "at": ISO8601, "message": { id, content } }`
- `{ "type": "assistant_block", "at": ISO8601, "data": { ...content block... } }`
- `{ "type": "tool_result", "at": ISO8601, "tool_use_id": string, "data": { output?, error?, base64_image?, system? } }`
- `{ "type": "api", "at": ISO8601, "data": { request: {method,url,headers}, response: {status,headers,body_preview}, error } }`
- `{ "type": "assistant_message", "at": ISO8601, "data": [ ...final assistant content blocks... ] }`
- `{ "type": "assistant_done", "at": ISO8601 }`

### Agent loop (`app/services/agent_runner.py`)

- Converts DB history to “beta” content format and calls `computer_use_demo.loop.sampling_loop(...)` with:
  - `model` from settings, `APIProvider.ANTHROPIC`, `api_key`
  - `tool_version = "computer_use_20250124"`, `max_tokens = 4096`
- Streams incremental blocks and tool results via callbacks
- Persists the final assistant message as `content_json` (structured) and emits terminal events

### VM lifecycle (`app/services/vm_manager.py`)

- Starts a Docker container from image `ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest` (override via `VM_BASE_IMAGE`)
- Publishes random host ports for `6080/tcp` (noVNC) and `5900/tcp` (VNC) and returns them in session metadata
- If Docker is unavailable, falls back to static ports `{ novnc_port: 6080, vnc_port: 5901 }`
- `POST /sessions/{id}/archive` attempts to stop/remove the container

### Event store (`app/services/event_store.py`)

- If `MONGODB_URI` is set and `pymongo` is available, events are appended to `computer_use.session_events`
- `GET /sessions/{id}/events` returns persisted events for replay
- If not configured, event methods no-op and the feature is effectively disabled

## Requirements

- Docker and docker-compose
- Anthropic API key

## Environment

Create `.env` in the project root:

```
ANTHROPIC_API_KEY=your_key_here
# DATABASE_URL=postgresql+psycopg2://app:app@db:5432/app
VNC_PASSWORD=vncpassword
# Optional:
# MONGODB_URI=mongodb://user:pass@host:27017
# FRONTEND_ORIGIN=http://localhost:8080
```

Default DB is SQLite at `./data/app.db`. To use Postgres, set `DATABASE_URL` accordingly.

## Run locally

```
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8080`
- noVNC: `http://localhost:6080`

Or development mode without Docker:

```
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API reference

### Create session

```
POST /sessions
{}
→ 200 OK: { id, title, status, created_at, updated_at, archived, last_agent_state, metadata_json }
```

### List sessions

```
GET /sessions
→ 200 OK: [ SessionRead, ... ]
```

### Get session with history

```
GET /sessions/{id}
→ 200 OK: { session: SessionRead, messages: MessageRead[] }
```

### Archive session

```
POST /sessions/{id}/archive
→ 200 OK: SessionRead
```

### Historical events (optional)

```
GET /sessions/{id}/events
→ 200 OK: [ { type, at, ... }, ... ]
```

### Send user message

```
POST /sessions/{id}/messages
{ "content": "Open a browser and go to anthropic.com" }
→ 200 OK: MessageRead (user message)
```

### WebSocket stream

```
WS /sessions/{id}/stream
← { "type": "user_message", ... }
← { "type": "assistant_block", ... }
← { "type": "tool_result", ... }
← { "type": "assistant_message", ... }
← { "type": "assistant_done", ... }
```

## Example usage (curl)

1) Create a session

```bash
curl -s -X POST http://localhost:8000/sessions | jq
```

2) Connect WebSocket at `ws://localhost:8000/sessions/<id>/stream`

3) Send a message

```bash
curl -s -X POST http://localhost:8000/sessions/<id>/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"Open a browser and go to anthropic.com"}' | jq
```

Observe incremental events over the WebSocket.

## Security, deployment, and ops notes

- Add authentication/authorization, rate limiting, and CSRF protections as appropriate
- Restrict CORS in `app/main.py` for production
- Replace auto table creation with migrations (e.g., Alembic)
- Harden Docker VM lifecycle and resource limits; ensure container cleanup on failures
- Add observability: structured logging, metrics, and tracing for agent/tool calls
- Back up databases; manage secrets via a vault or platform-specific secret store

## License

See `LICENSE`.
