import csv
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from .config import settings
from .db import Base, SessionLocal, engine
from .models import User

logger = logging.getLogger(__name__)


def _parse_fatturato(raw: str) -> Decimal:
    cleaned = raw.replace("€", "").replace(",", ".").strip()
    return Decimal(cleaned)


def _row_to_user(row: dict[str, str]) -> User:
    return User(
        nome=row["nome"],
        cognome=row["cognome"],
        regime=row["regime"],
        cassa=row["cassa"],
        commercialista=row["commercialista"],
        apertura_piva=datetime.strptime(row["apertura_piva"], "%d/%m/%Y").date(),
        fatturato_2025=_parse_fatturato(row["fatturato_2025"]),
        fatturato_2026=_parse_fatturato(row["fatturato_2026"]),
    )


def run() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        count = session.scalar(select(func.count(User.id)))
        if count:
            logger.info("users table already populated (%d rows); skipping seed", count)
            return
        with settings.csv_path.open(newline="", encoding="utf-8") as fh:
            users = [_row_to_user(row) for row in csv.DictReader(fh)]
        session.add_all(users)
        session.commit()
        logger.info("seeded %d users from %s", len(users), settings.csv_path)
