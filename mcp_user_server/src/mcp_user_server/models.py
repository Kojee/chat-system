from datetime import date
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(128))
    cognome: Mapped[str] = mapped_column(String(128))
    regime: Mapped[str] = mapped_column(String(64))
    cassa: Mapped[str] = mapped_column(String(64))
    commercialista: Mapped[str] = mapped_column(String(128))
    apertura_piva: Mapped[date]
    fatturato_2025: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fatturato_2026: Mapped[Decimal] = mapped_column(Numeric(12, 2))
