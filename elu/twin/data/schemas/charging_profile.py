from sqlmodel import SQLModel
from elu.twin.data.schemas.common import Index, Field
from sqlmodel import Field, SQLModel
from typing import List, Optional
from ocpp.v16.enums import (
    ChargingProfileKindType,
    ChargingProfilePurposeType,
    RecurrencyKind,
    ChargingRateUnitType,
)


class AssignedChargingProfile(SQLModel):
    id: Index = Field(default=None)
    chargingprofileid: int = Field(index=True)
    evse_id: int | None = Field(None)
    connector_id: int | None = Field(None)
    connector_0: bool = Field(True)
    stack_level: int
    charging_profile_purpose: ChargingProfilePurposeType
    charging_profile_kind: ChargingProfileKindType
    transaction_id: Optional[int] = None
    recurrency_kind: Optional[RecurrencyKind] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    charging_rate_unit: ChargingRateUnitType
    duration: Optional[int] = None
    start_schedule: Optional[str] = None
    min_charging_rate: Optional[float] = None
    charging_schedule_period: List["ChargingSchedulePeriod"] = Field(
        default_factory=list
    )


class ChargingSchedulePeriod(SQLModel):
    id: Index = Field(default=None)
    start_period: int
    limit: float
    number_phases: Optional[int] = None


# class SetChargingProfilePayload(SQLModel):
#     connector_id: int
#     cs_charging_profiles: Dict


class ChargingSchedule(SQLModel):
    charging_rate_unit: str
    charging_schedule_period: List[ChargingSchedulePeriod]
    duration: Optional[int] = None
    start_schedule: Optional[str] = None
    min_charging_rate: Optional[float] = None


class ChargingProfile(SQLModel):
    charging_profile_id: int
    stack_level: int
    charging_profile_purpose: str
    charging_profile_kind: str
    charging_schedule: ChargingSchedule
    transaction_id: Optional[int] = None
    recurrency_kind: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class SetChargingProfilePayload(SQLModel):
    connector_id: int
    cs_charging_profiles: ChargingProfile
    name: str = "charging_profile"
