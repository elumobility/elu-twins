from typing import Optional, List

from sqlmodel import Field, Relationship

from elu.twin.charge_point.charge_point.models.charge_point import (
    AssignedChargingProfile,
)
from elu.twin.data.enums import (
    EvseStatus,
)
from elu.twin.data.schemas.charge_point import ChargePointBase
from elu.twin.data.schemas.common import OwnedByUser, TableBase, Index
from elu.twin.data.schemas.connector import BaseConnector
from elu.twin.data.schemas.quota import QuotaBase
from elu.twin.data.schemas.token import BaseAppToken
from elu.twin.data.schemas.transaction import BaseTransaction
from elu.twin.data.schemas.user import BaseUser
from elu.twin.data.schemas.vehicle import VehicleBase
from elu.twin.data.schemas.ocpp_configuration import (
    OcppConfigurationV16Params,
    OcppConfigurationV16Base,
)
from elu.twin.data.schemas.auth import BaseAuthV16


class Quota(QuotaBase, TableBase, table=True):
    users: List["User"] = Relationship(back_populates="quota")


class User(BaseUser, TableBase, table=True):
    disabled: Optional[bool] = Field(default=False)
    hashed_password: str

    quota_id: Optional[Index] = Field(index=True, foreign_key="quota.id")
    quota: Quota = Relationship(back_populates="users")


class ChargePoint(ChargePointBase, OwnedByUser, table=True):
    name: str = Field(
        index=True, description="Charge point name", default="TwinCharger"
    )
    evses: List["Evse"] = Relationship(back_populates="charge_point")

    quota_id: Optional[Index] = Field(index=True, foreign_key="quota.id")
    ocpp_configuration_v16_id: Index | None = Field(
        default=None, foreign_key="ocppconfigurationv16.id"
    )
    # charging_profiles: List["ChargingProfile"] = Relationship(
    #     back_populates="charge_point"
    # )


class Evse(TableBase, table=True):
    evseid: int = Field(index=True)
    status: EvseStatus = Field(default=EvseStatus.unavailable)
    active_connector_id: int | None = Field(default=None)

    charge_point_id: Index | None = Field(default=None, foreign_key="chargepoint.id")
    charge_point: Optional[ChargePoint] = Relationship(back_populates="evses")

    connectors: List["Connector"] = Relationship(back_populates="evse")


class Connector(BaseConnector, table=True):
    evse_id: Index | None = Field(default=None, foreign_key="evse.id")
    evse: Optional[Evse] = Relationship(back_populates="connectors")

    transaction_id: Index | None = Field(default=None, foreign_key="transaction.id")
    vehicle_id: Index | None = Field(default=None, foreign_key="vehicle.id")


class Vehicle(VehicleBase, OwnedByUser, table=True):
    transaction_id: Index | None = Field(default=None, foreign_key="transaction.id")


# class ChargingProfile(AssignedChargingProfile, table=True):
#     id: int = Field(index=True)


class Transaction(BaseTransaction, OwnedByUser, table=True):
    charge_point_id: Index | None = Field(default=None)
    evse_id: Index | None = Field(default=None)
    connector_id: Index | None = Field(default=None)
    vehicle_id: Index | None = Field(default=None)


class AppToken(BaseAppToken, OwnedByUser, table=True):
    hashed_token: str = Field(description="Hashed token")


class OcppConfigurationV16(TableBase, OcppConfigurationV16Base, table=True):
    pass


#    charge_point_id: Index | None = Field(default=None, foreign_key="chargepoint.id")
#    charge_point: Optional[ChargePoint] = Relationship(back_populates="ocpp_configuration_v16")


class OcppAuthV16(BaseAuthV16, table=True):
    charge_point_id: Index | None = Field(default=None, foreign_key="chargepoint.id")
