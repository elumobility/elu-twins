from datetime import datetime

from sqlmodel import Field, SQLModel

from elu.twin.data.enums import TransactionStatus, TransactionName
from elu.twin.data.helpers import get_now
from elu.twin.data.schemas.common import Index, TableBase, OwnedByUser, UpdateSchema


class BaseTransaction(TableBase):
    start_time: datetime = Field(default_factory=get_now)
    end_time: datetime | None = Field(default=None)
    energy: int = Field(default=0, ge=0, description="Energy in kWh")
    status: TransactionStatus = Field(default=TransactionStatus.pending)
    transactionid: str | None = Field(default=None, description="Transaction ID")


class OutputTransaction(BaseTransaction):
    id: Index = Field(default=None)
    connector_id: Index = Field(index=True, description="Connector ID")
    vehicle_id: Index = Field(index=True, description="Vehicle ID")
    user_id: Index = Field(index=True, description="User ID")
    evse_id: Index = Field(index=True, description="EVSE ID")
    charge_point_id: Index = Field(index=True, description="Charge point ID")


class UpdateTransaction(UpdateSchema):
    end_time: datetime | None = None
    energy: int | None = None
    status: TransactionStatus | None = None
    transactionid: int | None = None


class RequestTransaction(SQLModel):
    pass


class RequestStartTransaction(RequestTransaction):
    connector_id: Index
    vehicle_id: Index | None = None


class RequestStopTransaction(RequestTransaction):
    transaction_id: Index


class RedisRequestTransaction(RequestTransaction):
    transaction_id: Index
    name: TransactionName


class RedisRequestStartTransaction(RedisRequestTransaction):
    name: TransactionName = TransactionName.start_transaction


class RedisRequestStopTransaction(RedisRequestTransaction):
    name: TransactionName = TransactionName.stop_transaction


class RedisRequestSetChargingProfile(SQLModel):
    pass
