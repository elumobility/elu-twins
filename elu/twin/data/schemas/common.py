from datetime import datetime

from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

Index = str


def get_uuid_str() -> str:
    return str(uuid4())


class IDBase(SQLModel):
    id: Index | None = Field(default_factory=get_uuid_str, primary_key=True, index=True)


class TimestampBase(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TableBase(IDBase, TimestampBase):
    pass


class OwnedByUser(TableBase):
    user_id: Index | None = Field(default=None, foreign_key="user.id")


class UpdateSchema(SQLModel):
    updated_at: datetime = Field(default_factory=datetime.utcnow)
