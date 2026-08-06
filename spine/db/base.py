from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic sees them via Base.metadata
from spine import models as _models  # noqa: E402,F401
