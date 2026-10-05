from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    DDL,
    Enum as SAEnum,
    ForeignKey,
    Identity,
    Index,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class MessageRole(str, Enum):
    user = "user"
    agent = "agent"


class AgentSettings(Base):
    __tablename__ = "agent_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)


# "Only one default row" constraint, declared as an EXCLUDE so it can be DEFERRABLE
# (partial unique *indexes* are not deferrable in Postgres, but EXCLUDE constraints are).
# A swap of the default flag (UPDATE old → false, UPDATE new → true) inside one
# transaction commits cleanly instead of tripping on the transient both-true state.
event.listen(
    AgentSettings.__table__,
    "after_create",
    DDL(
        "ALTER TABLE agent_settings ADD CONSTRAINT one_default_agent_setting "
        "EXCLUDE USING btree (is_default WITH =) WHERE (is_default) "
        "DEFERRABLE INITIALLY DEFERRED"
    ),
)


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (UniqueConstraint("user_id", "thread_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True)
    thread_id: Mapped[int] = mapped_column(Identity(start=1), unique=True, index=True)
    agent_settings_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_settings.id"), nullable=True, index=True
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", order_by="Message.created_at"
    )
    agent_settings: Mapped[AgentSettings | None] = relationship()


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)

    chat: Mapped[Chat] = relationship(back_populates="messages")
