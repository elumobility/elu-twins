from datetime import datetime
from sqlmodel import SQLModel, Field
from elu.twin.data.schemas.common import Index


class ActionMessageRequest(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str


class RequestConnectChargePoint(SQLModel):
    charge_point_id: Index


class RequestDisconnectChargePoint(SQLModel):
    charge_point_id: Index
