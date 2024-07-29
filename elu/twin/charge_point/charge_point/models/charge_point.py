from __future__ import annotations

from datetime import datetime

from elu.twin.data.enums import (
    TransactionName,
)
from elu.twin.data.schemas.charging_profile import SetChargingProfilePayload
from elu.twin.data.schemas.transaction import (
    RedisRequestStartTransaction,
    RedisRequestStopTransaction,
)

# from ocpp.v16.datatypes import ChargingProfile
from sqlmodel import SQLModel, Field


class Reservation(SQLModel):
    connector_id: int = Field(default=..., ge=0)
    expiry_date: datetime = Field(default=...)
    id_tag: str = Field(default=...)
    parent_id_tag: str | None = Field(default=None)
    reservation_id: int = Field(default=...)

    def get_reservation_id(self, id_tag: str, connector_id: int) -> int | None:
        if id_tag == id_tag and datetime.now() < self.expiry_date:
            if self.connector_id == 0 or self.connector_id == connector_id:
                return self.reservation_id
        return None


actions = {
    TransactionName.start_transaction: RedisRequestStartTransaction,
    TransactionName.stop_transaction: RedisRequestStopTransaction,
    "charging_profile": SetChargingProfilePayload,
}
