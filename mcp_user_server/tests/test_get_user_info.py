"""Verify get_user_info only ever returns the row matching the request-context user_id."""
from contextlib import contextmanager

import pytest

from mcp_user_server.context import current_user_id
from mcp_user_server.mcp_app import get_user_info

from .factories import UserFactory


@contextmanager
def _as_user(uid: int):
    token = current_user_id.set(uid)
    try:
        yield
    finally:
        current_user_id.reset(token)


def test_returns_caller_row():
    user = UserFactory(id=42, nome="Alice", cognome="Smith")
    with _as_user(user.id):
        result = get_user_info()
    assert result.id == user.id
    assert result.nome == "Alice"
    assert result.cognome == "Smith"


def test_does_not_leak_other_users():
    caller = UserFactory(id=1, nome="Alice", cognome="Smith")
    UserFactory(id=2, nome="Bob", cognome="Jones")
    with _as_user(caller.id):
        result = get_user_info()
    assert result.id == caller.id
    assert result.nome == "Alice"
    assert result.cognome == "Smith"


def test_missing_user_id_raises():
    UserFactory()
    with pytest.raises(ValueError, match="user_id missing"):
        get_user_info()


def test_unknown_user_id_raises():
    UserFactory()
    with _as_user(999):
        with pytest.raises(ValueError, match="not found"):
            get_user_info()
