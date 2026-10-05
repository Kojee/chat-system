import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from langchain_core.messages import AIMessageChunk
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .agent import build_agent
from .auth import USER_ID_COOKIE
from .db import AsyncSessionLocal
from .models import MessageRole
from .persistence import (
    ChatNotFound,
    get_default_agent_settings,
    get_or_create_chat,
    load_messages,
    resolve_chat_params,
    save_message,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginPayload(BaseModel):
    user_id: int


class LoginResponse(BaseModel):
    user_id: int


class NewChatResponse(BaseModel):
    thread_id: int
    agent_settings_id: int


class MessageView(BaseModel):
    role: MessageRole
    content: str


class SendMessagePayload(BaseModel):
    content: str


def _current_user_id(user_id: str = Cookie(alias=USER_ID_COOKIE)) -> int:
    try:
        return int(user_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="invalid user_id cookie") from e


def _checkpointer(request: Request) -> AsyncPostgresSaver:
    return request.app.state.checkpointer


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginPayload, response: Response) -> LoginResponse:
    response.set_cookie(
        USER_ID_COOKIE,
        str(payload.user_id),
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(user_id=payload.user_id)


@router.post("/chats", response_model=NewChatResponse)
async def create_chat(user_id: int = Depends(_current_user_id)) -> NewChatResponse:
    async with AsyncSessionLocal() as session:
        default_settings = await get_default_agent_settings(session)
        chat = await get_or_create_chat(
            session, user_id, None, agent_settings_id=default_settings.id
        )
        await session.commit()
        await session.refresh(chat)
        return NewChatResponse(
            thread_id=chat.thread_id, agent_settings_id=default_settings.id
        )


@router.get("/chats/{thread_id}/messages", response_model=list[MessageView])
async def list_messages(
    thread_id: int, user_id: int = Depends(_current_user_id)
) -> list[MessageView]:
    async with AsyncSessionLocal() as session:
        try:
            chat = await get_or_create_chat(session, user_id, thread_id)
        except ChatNotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        messages = await load_messages(session, chat.id)
        return [MessageView(role=m.role, content=m.content) for m in messages]


@router.post("/chats/{thread_id}/messages")
async def send_message(
    thread_id: int,
    payload: SendMessagePayload,
    request: Request,
    user_id: int = Depends(_current_user_id),
):
    async with AsyncSessionLocal() as session:
        try:
            chat = await get_or_create_chat(session, user_id, thread_id)
        except ChatNotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        chat_id = chat.id
        params = await resolve_chat_params(session, chat)

    async with AsyncSessionLocal() as session:
        await save_message(session, chat_id, MessageRole.user, payload.content)
        await session.commit()

    checkpointer = _checkpointer(request)
    agent = await build_agent(user_id, checkpointer, params)
    config = {"configurable": {"thread_id": str(thread_id)}}

    async def event_stream():
        collected: list[str] = []
        try:
            async for chunk, _meta in agent.astream(
                {"messages": [{"role": "user", "content": payload.content}]},
                config=config,
                stream_mode="messages",
            ):
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    collected.append(text)
                    yield {"event": "token", "data": text}
        except Exception as e:
            logger.exception("agent stream failed")
            yield {"event": "error", "data": str(e)}
            return

        final = "".join(collected)
        async with AsyncSessionLocal() as session:
            await save_message(session, chat_id, MessageRole.agent, final)
            await session.commit()

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_stream())
