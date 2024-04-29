import logging
from datetime import datetime

import aiohttp
from elu.twin.data.schemas.actions import ActionMessageRequest
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.transaction import (
    UpdateTransaction,
    OutputTransaction,
    RequestStartTransaction,
    RequestStopTransaction,
)
from elu.twin.data.schemas.vehicle import UpdateVehicle, OutputVehicle
from elu.twin.data.schemas.connector import UpdateConnector

from elu.twin.charge_point.env import BACKEND_PRIVATE_URL
from elu.twin.data.enums import (
    EvseStatus,
    PowerType,
    ConnectorStatus,
    VehicleStatus,
)

from ocpp.v16.enums import ChargePointStatus
from elu.twin.data.schemas.charge_point import OutputChargePoint, UpdateChargePoint
from elu.twin.data.schemas.ocpp_configuration import (
    OutputOcppConfigurationV16,
    OcppConfigurationV16Update,
)
from loguru import logger


API_PREFIX = "twin"
API_OCPP_PREFIX = f"{API_PREFIX}/ocpp"
API_OPERATIONS_PREFIX = f"operations/ocpp"
API_VEHICLE_PREFIX = f"{API_PREFIX}/vehicle"
API_QUOTA_PREFIX = f"{API_PREFIX}/quota"

headers = {"Content-Type": "application/json"}


async def get_charge_point(cid: Index) -> OutputChargePoint:
    """

    :param cid:
    :return:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/charge-point/{cid}"
    logging.info("Connecting to %s", url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                data = OutputChargePoint.model_validate(data)
                return data
            logging.warning(response.status)


async def get_charge_point_configuration(
    configuration_id: Index,
) -> OutputOcppConfigurationV16:
    """

    :return:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/charge-point/configuration/{configuration_id}"
    logging.info("Connecting to %s", url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                data = OutputOcppConfigurationV16.model_validate(data)
                return data
            logging.warning(response.status)


async def start_transaction(
    transaction: RequestStartTransaction, user_id: Index
) -> OutputTransaction | None:
    """

    :param transaction:
    :return:
    """
    url = f"{BACKEND_PRIVATE_URL}/twin/charge-point/action/start-transaction/{user_id}"
    logging.info("")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=headers, data=transaction.model_dump_json()
        ) as response:
            logging.warning(response.status)
            if response.status == 200:
                data = await response.json()
                data = OutputTransaction.model_validate(data)
                return data
            return None


async def stop_transaction(
    transaction: RequestStopTransaction, user_id: Index
) -> ActionMessageRequest | None:
    """

    :param transaction:
    :param user_id:
    """
    url = f"{BACKEND_PRIVATE_URL}/twin/charge-point/action/stop-transaction/{user_id}"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=headers, data=transaction.model_dump_json()
        ) as response:
            logging.warning(response.status)
            if response.status == 200:
                data = await response.json()
                data = ActionMessageRequest.model_validate(data)
                return data
            return None


async def update_chager_point_configuration(
    configuration_id: Index, configuration: OcppConfigurationV16Update
):
    """

    :param configuration_id:
    :return:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/charge-point/configuration/{configuration_id}"
    logging.warning(f"updating configuration: configuration_id: {configuration}")
    logging.info("Connecting to %s", url)
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url, headers=headers, data=configuration.model_dump_json()
        ) as response:
            logging.warning(response.status)
            logging.warning(response.text)


async def update_vehicle_soc(vid: Index, soc: float):
    update_vehicle = UpdateVehicle(soc=soc)
    url = f"{BACKEND_PRIVATE_URL}/{API_VEHICLE_PREFIX}/soc/{vid}"
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url, headers=headers, data=update_vehicle.model_dump_json()
        ) as response:
            logging.warning(response.status)


async def get_vehicle_battery(vid: Index):
    url = f"{BACKEND_PRIVATE_URL}/{API_VEHICLE_PREFIX}/vehicle/{vid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("battery_capacity")
            logging.warning(f"response: {response.status}")


async def get_vehicle(vid: Index) -> OutputVehicle:
    url = f"{BACKEND_PRIVATE_URL}/{API_VEHICLE_PREFIX}/{vid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                data = OutputVehicle.model_validate(data)
                return data
            logging.warning(f"response: {response.status}")


async def update_charger_status(cid: Index, status: ChargePointStatus):
    """

    :param cid:
    :param status:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/charge-point/status/{cid}/{status.value}"
    async with aiohttp.ClientSession() as session:
        async with session.put(url) as response:
            logging.warning(response.status)


async def update_evse_status(
    evse_id: Index, status: EvseStatus, active_connector: int | None = None
):
    """

    :param evse_id:
    :param status:
    :param active_connector:
    """
    logger.debug(f"active connector: {active_connector}")
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/evse/status/{evse_id}/{status}"
    params = {} if active_connector is None else {"active_connector": active_connector}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, params=params) as response:
            logging.warning(response.status)


async def update_connector_status(connector_id: Index, status: ConnectorStatus):
    """

    :param connector_id:
    :param status:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/connector/status/{connector_id}/{status.value}"
    async with aiohttp.ClientSession() as session:
        async with session.put(url) as response:
            logging.warning(response.status)


async def update_connector_values(
    connector_id: Index, connector_update: UpdateConnector
):
    """

    :param connector_id:
    :param connector_update:
    """

    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/connector/{connector_id}"
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.put(
            url, headers=headers, data=connector_update.model_dump_json()
        ) as response:
            logging.warning(response.status)


async def get_transaction(transaction_id: Index) -> OutputTransaction:
    """

    :param transaction_id:
    :return:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OPERATIONS_PREFIX}/transaction/{transaction_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                data = OutputTransaction.model_validate(data)
                return data
            logging.warning(response.status)


async def update_transaction(
    transaction_id: Index, transaction_update: UpdateTransaction
):
    """

    :param transaction_id:
    :param transaction_update:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OPERATIONS_PREFIX}/transaction/{transaction_id}"
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.patch(
            url, headers=headers, data=transaction_update.model_dump_json()
        ) as response:
            logging.warning(response.status)


async def get_charging_rate(
    vid: Index, soc: float, power_type: PowerType = PowerType.dc
):
    """

    :param vid:
    :param soc:
    :param power_type:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/vehicle/charging-rate/{vid}/{power_type}/{soc}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("power")
            logging.warning(response.status)


async def update_heartbeat(cid: Index, heartbeat: datetime):
    """

    :param cid:
    """
    headers = {"Content-Type": "application/json"}
    update = UpdateChargePoint(last_heartbeat=heartbeat)
    url = f"{BACKEND_PRIVATE_URL}/{API_OCPP_PREFIX}/charge-point/{cid}"
    async with aiohttp.ClientSession() as session:
        async with session.patch(
            url, headers=headers, data=update.model_dump_json()
        ) as response:
            logging.warning(response.status)


async def consume_quota(quota_id: Index, cost: int):
    """

    :param quota_id:
    :param cost:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_QUOTA_PREFIX}/{quota_id}/{cost}"
    async with aiohttp.ClientSession() as session:
        async with session.patch(url) as response:
            if response.status == 200:
                _ = await response.json()
            logging.warning(response.status)


async def update_vehicle_status(vid: Index, status: VehicleStatus):
    """

    :param vid:
    :param status:
    """
    url = f"{BACKEND_PRIVATE_URL}/{API_VEHICLE_PREFIX}/status/{vid}/{status}"
    async with aiohttp.ClientSession() as session:
        async with session.put(url) as response:
            logging.warning(response.status)


# async def clear_cache(user_id: str, cid: str):
#    async with aiohttp.ClientSession() as session:
#        async with session.put(
#            f"{BACKEND_PRIVATE_URL}/charge-point/cache-clear/{user_id}/{cid}"
#        ) as resp:
#            print(resp.status)
#            return None


# async def update_auth_list(
#     user_id: str, cid: str, version: int, auth_list: list[AuthorizationData]
# ):
#     async with aiohttp.ClientSession() as session:
#         async with session.put(
#             f"{BACKEND_PRIVATE_URL}/charge-point/auth-list/{user_id}/{cid}/{version}",
#             json=[asdict(auth) for auth in auth_list],
#         ) as resp:
#             print(resp.status)
#             return None
#
#
# async def cancel_reservation(user_id: str, cid: str, reservation_id: int):
#     async with aiohttp.ClientSession() as session:
#         async with session.put(
#             f"{BACKEND_PRIVATE_URL}/charge-point/cancel-reservation/{user_id}/{cid}/{reservation_id}"
#         ) as resp:
#             print(resp.status)
#             return None
