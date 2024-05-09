from elu.twin.data.schemas.charge_point import OutputChargePoint as Cpi
import requests
from elu.twin.data.enums import (
    EvseStatus,
    ConnectorStatus,
)


async def update_evse_and_connectors(cpi: Cpi):
    for evse in cpi.evses:
        evse.status = EvseStatus.available
        await requests.update_evse_status(
            evse_id=evse.id,
            status=evse.status,
        )
        for connector in evse.connectors:
            connector.status = ConnectorStatus.available
            await requests.update_connector_status(
                connector_id=connector.id,
                status=connector.status,
            )
