from datetime import datetime
from sqlmodel import SQLModel, Field

from elu.twin.data.helpers import get_now
from elu.twin.data.schemas.common import Index
from ocpp.v201.enums import BootReasonType

3


class ActionMessageRequest(SQLModel):
    created_at: datetime = Field(default_factory=get_now)
    message: str


class RequestConnectChargePoint(SQLModel):
    charge_point_id: Index
    boot_reason: BootReasonType | None = Field(default=None)


class RequestDisconnectChargePoint(SQLModel):
    charge_point_id: Index
