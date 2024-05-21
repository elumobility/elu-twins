from ocpp.v16.datatypes import ChargingProfile
from sqlmodel import SQLModel
from elu.twin.data.schemas.common import Index, Field


class ChargePointProfile(SQLModel):
    transaction_id: Index = Field(index=True, description="transaction ID")
    charge_point_profile: ChargingProfile
