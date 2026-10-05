from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_params import AgentParams
from .config import settings
from .models import AgentSettings, Chat, Message, MessageRole


class ChatNotFound(Exception):
    pass


class NoDefaultAgentSettings(Exception):
    pass


async def seed_default_agent_settings(session: AsyncSession) -> AgentSettings:
    """Insert the bootstrap default settings if the table is empty.

    The bootstrap values come from pydantic-settings (config.py) — that's the
    only place they live going forward; future variants are inserted into the
    table directly (no further code changes needed to swap defaults).
    """
    existing = await session.scalar(select(AgentSettings).where(AgentSettings.is_default == True))  # noqa: E712
    if existing is not None:
        return existing

    params = AgentParams(
        system_prompt=settings.system_prompt_path.read_text(encoding="utf-8"),
        model_name=settings.openai_model,
        has_summarizer=True,
        summarizer_model_name=settings.openai_model,
        summarization_max_tokens=settings.summarization_max_tokens,
    )
    row = AgentSettings(name="default-v1", is_default=True, params=params.model_dump())
    session.add(row)
    await session.flush()
    return row


async def get_default_agent_settings(session: AsyncSession) -> AgentSettings:
    stmt = select(AgentSettings).where(AgentSettings.is_default == True)  # noqa: E712
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NoDefaultAgentSettings("no default agent_settings row present")
    return row


async def get_agent_settings(session: AsyncSession, settings_id: int) -> AgentSettings:
    row = await session.get(AgentSettings, settings_id)
    if row is None:
        raise NoDefaultAgentSettings(f"agent_settings id={settings_id} not found")
    return row


async def get_or_create_chat(
    session: AsyncSession,
    user_id: int,
    thread_id: int | None,
    agent_settings_id: int | None = None,
) -> Chat:
    if thread_id is None:
        chat = Chat(user_id=user_id, agent_settings_id=agent_settings_id)
        session.add(chat)
        await session.flush()
        return chat

    stmt = select(Chat).where(Chat.user_id == user_id, Chat.thread_id == thread_id)
    chat = (await session.execute(stmt)).scalar_one_or_none()
    if chat is None:
        raise ChatNotFound(f"no chat with thread_id={thread_id} for user {user_id}")
    return chat


async def save_message(
    session: AsyncSession, chat_id: int, role: MessageRole, content: str
) -> None:
    session.add(Message(chat_id=chat_id, role=role, content=content))


async def load_messages(session: AsyncSession, chat_id: int) -> list[Message]:
    stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    return list((await session.execute(stmt)).scalars().all())


async def resolve_chat_params(session: AsyncSession, chat: Chat) -> AgentParams:
    """The chat's bound settings if set, otherwise the current default."""
    if chat.agent_settings_id is not None:
        row = await get_agent_settings(session, chat.agent_settings_id)
    else:
        row = await get_default_agent_settings(session)
    return AgentParams.model_validate(row.params)
