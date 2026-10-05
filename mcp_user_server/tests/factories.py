from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from mcp_user_server.models import User


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n + 1)
    nome = factory.Faker("first_name", locale="it_IT")
    cognome = factory.Faker("last_name", locale="it_IT")
    regime = "Forfettario"
    cassa = "GS INPS"
    commercialista = factory.Faker("name", locale="it_IT")
    apertura_piva = factory.Faker("date_object")
    fatturato_2025 = factory.LazyFunction(lambda: Decimal("0.00"))
    fatturato_2026 = factory.LazyFunction(lambda: Decimal("0.00"))
