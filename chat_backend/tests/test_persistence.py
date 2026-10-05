import asyncio

import pytest
from sqlalchemy import func, select, text

from chat_backend.agent_params import AgentParams
from chat_backend.models import AgentSettings, Chat, Message, MessageRole
from chat_backend.persistence import (
    ChatNotFound,
    get_or_create_chat,
    load_messages,
    resolve_chat_params,
    save_message,
    seed_default_agent_settings,
)


# ---------- helpers ----------

DEFAULT_PARAMS_DICT = AgentParams(
    system_prompt="test prompt",
    model_name="gpt-4o-mini",
    has_summarizer=False,
).model_dump()


async def _insert_settings(session, *, name: str, is_default: bool, params=None) -> AgentSettings:
    row = AgentSettings(
        name=name,
        is_default=is_default,
        params=params or DEFAULT_PARAMS_DICT,
    )
    session.add(row)
    await session.flush()
    return row


# ---------- seed_default_agent_settings ----------


async def test_seed_default_agent_settings_creates_row_when_empty(session):
    row = await seed_default_agent_settings(session)
    await session.flush()
    assert row.is_default is True
    assert row.name == "default-v1"
    AgentParams.model_validate(row.params)  # raises if shape drifted

    count = await session.scalar(select(func.count(AgentSettings.id)))
    assert count == 1


async def test_seed_default_agent_settings_is_idempotent(session):
    first = await seed_default_agent_settings(session)
    second = await seed_default_agent_settings(session)
    await session.flush()
    assert first.id == second.id
    count = await session.scalar(select(func.count(AgentSettings.id)))
    assert count == 1


# ---------- get_or_create_chat ----------


async def test_get_or_create_chat_new_thread_assigns_id(session):
    settings_row = await _insert_settings(session, name="t", is_default=True)
    chat = await get_or_create_chat(session, user_id=1, thread_id=None, agent_settings_id=settings_row.id)
    assert chat.thread_id is not None
    assert chat.user_id == 1
    assert chat.agent_settings_id == settings_row.id


async def test_get_or_create_chat_resolves_existing(session):
    settings_row = await _insert_settings(session, name="t", is_default=True)
    created = await get_or_create_chat(session, 1, None, agent_settings_id=settings_row.id)
    await session.flush()
    resolved = await get_or_create_chat(session, 1, created.thread_id)
    assert resolved.id == created.id


async def test_get_or_create_chat_raises_for_wrong_user(session):
    settings_row = await _insert_settings(session, name="t", is_default=True)
    created = await get_or_create_chat(session, 1, None, agent_settings_id=settings_row.id)
    await session.flush()
    with pytest.raises(ChatNotFound):
        await get_or_create_chat(session, user_id=2, thread_id=created.thread_id)


# ---------- save_message / load_messages ----------


async def test_save_message_persists(session):
    settings_row = await _insert_settings(session, name="t", is_default=True)
    chat = await get_or_create_chat(session, 1, None, agent_settings_id=settings_row.id)
    await session.flush()

    await save_message(session, chat.id, MessageRole.user, "ciao")
    await session.flush()

    rows = (await session.execute(select(Message).where(Message.chat_id == chat.id))).scalars().all()
    assert len(rows) == 1
    assert rows[0].role == MessageRole.user
    assert rows[0].content == "ciao"


async def test_load_messages_ordered_chronologically(session):
    settings_row = await _insert_settings(session, name="t", is_default=True)
    chat = await get_or_create_chat(session, 1, None, agent_settings_id=settings_row.id)
    await session.flush()

    # Insert in a non-chronological order; load_messages should still return them by created_at asc.
    await save_message(session, chat.id, MessageRole.user, "first")
    await session.flush()
    await asyncio.sleep(0.01)  # ensure distinct created_at values at server side
    await save_message(session, chat.id, MessageRole.agent, "second")
    await session.flush()
    await asyncio.sleep(0.01)
    await save_message(session, chat.id, MessageRole.user, "third")
    await session.flush()

    messages = await load_messages(session, chat.id)
    assert [m.content for m in messages] == ["first", "second", "third"]


# ---------- resolve_chat_params ----------


async def test_resolve_chat_params_uses_chat_binding(session):
    default_row = await _insert_settings(session, name="default", is_default=True)
    variant_params = AgentParams(
        system_prompt="variant prompt",
        model_name="gpt-4o",
        has_summarizer=False,
    ).model_dump()
    variant_row = await _insert_settings(
        session, name="variant", is_default=False, params=variant_params
    )

    chat = await get_or_create_chat(session, 1, None, agent_settings_id=variant_row.id)
    await session.flush()
    await session.refresh(chat)

    params = await resolve_chat_params(session, chat)
    assert params.system_prompt == "variant prompt"
    assert params.model_name == "gpt-4o"
    assert default_row.is_default is True  # default still exists, just wasn't used


async def test_resolve_chat_params_falls_back_to_default_when_unbound(session):
    await _insert_settings(session, name="the-default", is_default=True)
    chat = await get_or_create_chat(session, 1, None, agent_settings_id=None)
    await session.flush()
    await session.refresh(chat)
    assert chat.agent_settings_id is None  # confirm legacy/unbound state

    params = await resolve_chat_params(session, chat)
    assert params.system_prompt == DEFAULT_PARAMS_DICT["system_prompt"]


# ---------- EXCLUDE constraint behavior ----------


async def test_exclude_constraint_allows_default_swap_in_one_transaction(session):
    old = await _insert_settings(session, name="old", is_default=True)
    new_params = AgentParams(
        system_prompt="new",
        model_name="gpt-4o-mini",
        has_summarizer=False,
    ).model_dump()
    new = AgentSettings(name="new", is_default=True, params=new_params)
    session.add(new)
    await session.execute(
        text("UPDATE agent_settings SET is_default = false WHERE id = :id"),
        {"id": old.id},
    )
    await session.flush()  # would raise if the EXCLUDE weren't DEFERRABLE

    defaults = (
        await session.execute(select(AgentSettings).where(AgentSettings.is_default == True))  # noqa: E712
    ).scalars().all()
    assert len(defaults) == 1
    assert defaults[0].name == "new"
