from datetime import date
from decimal import Decimal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from .context import current_user_id
from .db import SessionLocal
from .models import User


class UserInfo(BaseModel):
    """Tax profile for the authenticated user."""

    id: int
    nome: str
    cognome: str
    regime: str = Field(description="Regime fiscale, e.g. Forfettario, Semplificato, Ordinario")
    cassa: str = Field(description="Cassa previdenziale, e.g. GS INPS, INARCASSA, ENPAP")
    commercialista: str
    apertura_piva: date
    fatturato_2025: Decimal
    fatturato_2026: Decimal


mcp = FastMCP(
    "user-mcp-server",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def get_user_info() -> UserInfo:
    """
    Return the authenticated user's tax-profile data.

    The user_id is supplied by the MCP Host through an HTTP header, so this
    tool intentionally takes no parameters: the LLM cannot influence which
    user is read.
    """
    user_id = current_user_id.get()
    if user_id is None:
        raise ValueError("user_id missing from request context")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"user {user_id} not found")
        return UserInfo.model_validate(user, from_attributes=True)
