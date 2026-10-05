from contextvars import ContextVar

current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
current_api_key: ContextVar[str | None] = ContextVar("current_api_key", default=None)
