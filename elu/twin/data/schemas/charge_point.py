from datetime import datetime
from typing import List, Optional

from ocpp.v16.enums import ChargePointStatus
from ocpp.v201.enums import BootReasonType
from sqlmodel import Field, SQLModel
from ocpp.v16.datatypes import (
    AuthorizationData,
)


from elu.twin.data.schemas.common import Index, UpdateSchema
from elu.twin.data.enums import AuthorizationStatus, Protocol
from elu.twin.data.schemas.evse import InputEvse, OutputEvse
from elu.twin.data.schemas.charging_profile import AssignedChargingProfile
from elu.twin.data.utils import generate_cid


# class IdTagInfo(SQLModel):
#     expiry_date: datetime | None = Field(default=None)
#     id_tag: str = Field(index=True)
#     status: AuthorizationStatus


# class LocalAuthList(SQLModel):
#     entries: list[IdTagInfo] = []


class ChargePointBase(SQLModel):
    name: str = Field(
        index=True, description="Charge point name", default="TwinCharger"
    )
    cid: str = Field(default_factory=generate_cid)
    vendor: str = Field(default="Elu Twin")
    model: str = Field(default="Digital Twin")
    password: str = Field(default="1234")
    csms_url: str | None = Field(default=None)
    ocpp_protocol: Protocol = Field(default=Protocol.v16)
    boot_reason: BootReasonType | None = Field(default=None)
    voltage_ac: int = Field(default=230, ge=0, description="Voltage AC in V")
    voltage_dc: int = Field(default=400, ge=0, description="Voltage DC in V")
    maximum_dc_power: int = Field(
        default=60, ge=0, description="Maximum DC power in one connector in kWh"
    )
    maximum_ac_power: int = Field(
        default=20, ge=0, description="Maximum AC power in one connector in kWh"
    )
    status: ChargePointStatus = Field(default=ChargePointStatus.unavailable)
    charge_point_task_id: str | None = Field(default=None)
    last_heartbeat: datetime | None = Field(default=None)
    token_cost_per_minute: int = Field(
        default=0, ge=0, description="Token cost per minute"
    )


class InputChargePoint(ChargePointBase):
    evses: List[InputEvse] = Field(
        default_factory=list, description="List of connectors, per EVSEs"
    )


class OutputSimpleChargePoint(ChargePointBase):
    id: Index | None = Field(default=None)
    quota_id: Index | None = Field(default=None)
    ocpp_configuration_v16_id: Index | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class OutputChargePoint(OutputSimpleChargePoint):
    evses: List[OutputEvse] = Field(default_factory=list)
    local_auth_list: list[AuthorizationData] = Field(default_factory=list)
    charging_profiles: List[AssignedChargingProfile] = Field(default_factory=list)

    user_id: Index | None = Field(default=None)
    authorization_list_version: int = Field(default=0)


class UpdateChargePoint(UpdateSchema):
    name: Optional[str] = None
    csms_url: Optional[str] = None
    maximum_dc_power: Optional[int] = None
    maximum_ac_power: Optional[int] = None
    last_heartbeat: Optional[datetime] = None


class ChargePointString(SQLModel):
    charge_point_string: str
    csms_url: Optional[str] = None
    password: Optional[str] = None
