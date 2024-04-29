from typing import List

from sqlmodel import Field, SQLModel

from elu.twin.data.schemas.common import TableBase, Index
from elu.twin.data.enums import EvseStatus
from elu.twin.data.schemas.connector import OutputConnector, InputConnector


class InputEvse(SQLModel):
    connectors: List[InputConnector] = Field(
        default_factory=list, description="List of connectors"
    )


class OutputSimpleEvse(TableBase):
    id: Index = Field(default=None)
    evseid: int = Field(index=True)
    status: EvseStatus = Field(default=EvseStatus.unavailable)
    active_connector_id: int | None = Field(default=None)


class OutputEvse(OutputSimpleEvse):
    connectors: List[OutputConnector] = Field(default_factory=list)
