# Computer Use Agent (FastAPI)

A FastAPI backend that reuses Anthropic computer-use agent stack (from `anthropic-quickstarts/computer-use-demo`) and replaces the experimental Streamlit UI with REST/WebSocket APIs, database persistence, and a minimal HTML/JS frontend. Includes Docker and docker-compose for local development and deployment.

## Features

- FastAPI backend with CORS
- SQLite (default) or Postgres via `DATABASE_URL` with SQLAlchemy ORM
- WebSocket `/sessions/{id}/stream` for real-time updates
- Sessions and messages persistence
- Minimal frontend (static HTML/JS) served by nginx container
- Desktop container with noVNC for visual VNC access
- Dockerfile and docker-compose

## Requirements

- Docker and docker-compose
- Anthropic API key

## Environment

Create `.env` in the project root:

```
ANTHROPIC_API_KEY=your_key_here
# DATABASE_URL=postgresql+psycopg2://app:app@db:5432/app
VNC_PASSWORD=vncpassword
```

Default DB is SQLite at `./data/app.db`. To use Postgres, set `DATABASE_URL` accordingly.

## Run locally

```
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8080`
- noVNC: `http://localhost:6080`

## API

- `POST /sessions` → create a session
- `GET /sessions/{id}` → get session and chat history
- `POST /sessions/{id}/messages` → send message to agent (streams to WebSocket)
- `GET /sessions/{id}/stream` → WebSocket for live updates

### Example

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

See events streaming in WebSocket.

## Development

Install locally (optional):

```
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Notes

- This demo triggers Anthropic computer-use via the SDK tools. Ensure your model and account have computer-use enabled.
- For production, use Alembic migrations and secure your API (auth, rate limiting). This repo aims to demonstrate architecture and end-to-end plumbing.
