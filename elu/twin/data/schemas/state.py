from datetime import datetime

from sqlmodel import SQLModel, Field

from elu.twin.data.schemas.common import UpdateSchema
from elu.twin.data.schemas.location import Location


class State(SQLModel):
    location: Location | None = Field(default=None)
    speed: float = Field(default=0)
    odometer: float = Field(default=0)
    energy_source_level: float | None = Field(default=10)
    timestamp: datetime | None = Field(default=None)


class StateUpdate(UpdateSchema):
    location: Location | None = Field(default=None)
    speed: float | None = Field(default=None)
    odometer: float | None = Field(default=None)
    energy_source_level: float | None = Field(default=None)
    timestamp: datetime | None = Field(default=None)
