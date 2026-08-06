import uuid

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # Store UUIDs as strings everywhere.
        #
        # This keeps the schema simple and avoids UUID/varchar operator issues
        # if the DB was initialized with string PKs.
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        as_uuid = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(as_uuid)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
