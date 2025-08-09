import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session as OrmSession

from ..config import get_settings
from ..models.message import Message as MessageModel
from ..models.session import Session as SessionModel
from ..services.stream_manager import stream_manager

from computer_use_demo.loop import (
    sampling_loop,
    APIProvider,
)
from computer_use_demo.tools.groups import ToolVersion


settings = get_settings()


def db_add_message(
    db: OrmSession,
    session_id: str,
    role: str,
    content: Optional[str] = None,
    content_json: Optional[Dict[str, Any]] = None,
) -> MessageModel:
    msg = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        content_json=content_json,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def build_beta_messages(db_messages: List[MessageModel]) -> List[Dict[str, Any]]:
    beta_messages: List[Dict[str, Any]] = []
    for m in db_messages:
        if m.role == "user":
            beta_messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": m.content or ""},
                    ],
                }
            )
        elif m.role == "assistant":
            if m.content_json and isinstance(m.content_json, list):
                beta_messages.append({"role": "assistant", "content": m.content_json})
            elif m.content:
                beta_messages.append(
                    {"role": "assistant", "content": [{"type": "text", "text": m.content}]}
                )
    return beta_messages


async def run_agent_for_new_user_message(
    db: OrmSession,
    session: SessionModel,
    user_message: MessageModel,
) -> None:
    # Build history
    db.refresh(session)
    beta_messages = build_beta_messages(session.messages)

    # callbacks
    def output_callback(block: Dict[str, Any]):
        # Stream each assistant content block as it arrives
        asyncio.get_event_loop().create_task(
            stream_manager.broadcast(
                session.id,
                {
                    "type": "assistant_block",
                    "at": datetime.utcnow().isoformat(),
                    "data": block,
                },
            )
        )

    def tool_output_callback(tool_result, tool_use_id: str):
        asyncio.get_event_loop().create_task(
            stream_manager.broadcast(
                session.id,
                {
                    "type": "tool_result",
                    "at": datetime.utcnow().isoformat(),
                    "tool_use_id": tool_use_id,
                    "data": {
                        "output": getattr(tool_result, "output", None),
                        "error": getattr(tool_result, "error", None),
                        "base64_image": getattr(tool_result, "base64_image", None),
                        "system": getattr(tool_result, "system", None),
                    },
                },
            )
        )

    def api_response_callback(request, response_or_body, error):
        # Detailed API request/response event for live stream
        try:
            method = getattr(request, "method", None)
            url = str(getattr(request, "url", ""))
            headers = dict(getattr(request, "headers", {}) or {})
        except Exception:
            method = None
            url = None
            headers = {}

        status_code = None
        resp_headers = {}
        body_preview = None
        if error is not None:
            try:
                body_preview = str(getattr(error, "body", None))
            except Exception:
                body_preview = str(error)
        else:
            try:
                status_code = getattr(response_or_body, "status_code", None)
                resp_headers = dict(getattr(response_or_body, "headers", {}) or {})
                # best-effort body preview
                text = getattr(response_or_body, "text", None)
                if callable(text):
                    text = text()
                if text:
                    body_preview = (text[:1000] + "…") if len(text) > 1000 else text
            except Exception:
                pass

        event = {
            "type": "api",
            "at": datetime.utcnow().isoformat(),
            "data": {
                "request": {"method": method, "url": url, "headers": headers},
                "response": {"status": status_code, "headers": resp_headers, "body_preview": body_preview},
                "error": str(error) if error else None,
            },
        }
        asyncio.get_event_loop().create_task(stream_manager.broadcast(session.id, event))

    # Run the sampling loop for one turn
    updated_messages = await sampling_loop(
        system_prompt_suffix="",
        model=settings.anthropic_model,
        provider=APIProvider.ANTHROPIC,
        messages=beta_messages + [
            {
                "role": "user",
                "content": [{"type": "text", "text": user_message.content or ""}],
            }
        ],
        output_callback=output_callback,
        tool_output_callback=tool_output_callback,
        api_response_callback=api_response_callback,
        api_key=settings.anthropic_api_key or "",
        only_n_most_recent_images=None,
        tool_version="computer_use_20250124",  # aligns with demo tools
        max_tokens=4096,
        thinking_budget=None,
        token_efficient_tools_beta=False,
    )

    # Persist the last assistant message content_json
    # Find the last assistant message in updated_messages
    last_assistant_content = None
    for msg in reversed(updated_messages):
        if msg.get("role") == "assistant":
            last_assistant_content = msg.get("content")
            break

    if last_assistant_content is not None:
        db_add_message(db, session.id, role="assistant", content_json=last_assistant_content)
        await stream_manager.broadcast(
            session.id,
            {
                "type": "assistant_message",
                "at": datetime.utcnow().isoformat(),
                "data": last_assistant_content,
            },
        )
        await stream_manager.broadcast(session.id, {"type": "assistant_done", "at": datetime.utcnow().isoformat()})


