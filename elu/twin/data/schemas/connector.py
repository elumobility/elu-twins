from ocpp.v201.enums import ConnectorType
from sqlmodel import SQLModel, Field

from elu.twin.data.schemas.common import TableBase, Index, UpdateSchema
from elu.twin.data.enums import ConnectorStatus, ConnectorQueuedActions


class InputConnector(SQLModel):
    connector_type: ConnectorType = Field(
        default=ConnectorType.c_ccs1, description="Connector type"
    )


class BaseConnector(TableBase):
    connectorid: int = Field(
        index=True, description="Connector ID, unique per charge point and EVSE"
    )
    status: ConnectorStatus = Field(default=ConnectorStatus.unavailable)
    current_dc_power: int = Field(default=0, ge=0, description="Current power in kWh")
    current_dc_current: int = Field(default=0, ge=0, description="Current current in A")
    current_dc_voltage: int = Field(default=0, ge=0, description="Current voltage in V")
    current_ac_power: int = Field(default=0, ge=0, description="Current power in kWh")
    current_ac_current: int = Field(default=0, ge=0, description="Current current in A")
    current_ac_voltage: int = Field(default=0, ge=0, description="Current voltage in V")
    current_energy: float = Field(
        default=0.0, ge=0.0, description="Current energy in kWh"
    )
    total_energy: float = Field(default=0.0, ge=0.0, description="Total energy in kWh")
    soc: int | None = Field(
        default=None, ge=0, le=100, description="State of charge in %"
    )
    connector_type: ConnectorType = Field(default=ConnectorType.c_ccs1)
    id_tag: str | None = Field(default=None)
    transactionid: int | None = Field(default=None)


class OutputConnector(BaseConnector):
    id: Index = Field(default=None)
    queued_action: list[ConnectorQueuedActions] = Field(default_factory=list)
    transaction_id: Index | None = Field(default=None)
    vehicle_id: Index | None = Field(default=None)


class UpdateConnector(UpdateSchema):
    current_dc_power: int | None = None
    current_dc_current: int | None = None
    current_dc_voltage: int | None = None
    current_energy: float | None = None
    total_energy: float | None = None
    soc: int | None = None
    id_tag: str | None = None
    transactionid: int | None = None
