from typing import Optional

from sqlmodel import Field, SQLModel

from elu.twin.data.schemas.common import TimestampBase, Index, UpdateSchema
from elu.twin.data.enums import VehicleStatus
from elu.twin.data.utils import generate_id_tag


class VehicleBase(SQLModel):
    name: str = Field(index=True)
    id_tag_suffix: str = Field(default_factory=generate_id_tag)
    battery_capacity: int = Field(ge=0, description="Battery capacity in kWh")
    maximum_dc_charging_rate: int = Field(
        default=50, ge=0, description="Maximum DC charging power"
    )
    maximum_ac_charging_rate: int = Field(
        default=50, ge=0, description="Maximum AC charging power"
    )
    soc: float = Field(default=10, ge=0, le=100, description="State of charge")
    status: VehicleStatus = Field(default=VehicleStatus.ready_to_charge)


class InputVehicle(VehicleBase):
    pass


class OutputVehicle(VehicleBase, TimestampBase):
    id: Index
    transaction_id: Index | None = Field(default=None)


class UpdateVehicle(UpdateSchema):
    name: Optional[str] = None
    battery_capacity: int | None = None
    maximum_charging_rate: int | None = None
    soc: float | None = None
    status: VehicleStatus | None = None
