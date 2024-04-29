import asyncio
import json
import logging

import websockets
from celery import Celery
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.charge_point import OutputChargePoint
from loguru import logger
from websockets import Subprotocol

from elu.twin.charge_point import requests
from elu.twin.charge_point.security import basic_auth_header
from elu.twin.charge_point.env import (
    REDIS_HOSTNAME,
    REDIS_PORT,
    CELERY_FACTORY_NAME,
    REDIS_DB_CELERY,
)
from elu.twin.data.enums import Protocol

from elu.twin.charge_point.charge_point.v16.charge_point import (
    ChargePoint as CpV16,
)
from elu.twin.charge_point.charge_point.v201.charge_point import (
    ChargePoint as CpV201,
)
from asgiref.sync import async_to_sync

app_celery = Celery(
    CELERY_FACTORY_NAME,
    broker=f"redis://{REDIS_HOSTNAME}:{REDIS_PORT}/{REDIS_DB_CELERY}",
)


async def create_charger_async(charge_point_id: Index):
    """

    :param charge_point_id:
    :return:
    """
    cpi: OutputChargePoint = await requests.get_charge_point(charge_point_id)
    configuration = await requests.get_charge_point_configuration(
        cpi.ocpp_configuration_v16_id
    )
    logging.info(f"Connecting to {cpi.csms_url}/{cpi.cid}")
    logging.warning("Starting charge point twin")
    ssl_context = True if cpi.csms_url.startswith("wss") else None
    async with websockets.connect(
        f"{cpi.csms_url}/{cpi.cid}",
        subprotocols=[Subprotocol(cpi.ocpp_protocol)],
        ssl=ssl_context,
        extra_headers=[basic_auth_header(cpi.cid, cpi.password)],
    ) as ws:
        try:
            if cpi.ocpp_protocol == Protocol.v16:
                logger.warning("Create V16 station")
                cp = CpV16(cpi.cid, ws)
            elif cpi.ocpp_protocol == Protocol.v201:
                logger.warning("Create V201 station")
                cp = CpV201(cpi.cid, ws)
            else:
                raise Exception(f"Invalid protocol {cpi.ocpp_protocol}")
            cp.cpi = cpi
            cp.ocpp_configuration = configuration
            await asyncio.gather(*cp.get_processes())
        except websockets.ConnectionClosed as e:
            logging.warning(f"Connections closed {cpi.cid}", e)


@app_celery.task
def create_charger(input: str):
    charge_point_id = json.loads(input).get("charge_point_id")
    async_to_sync(create_charger_async)(charge_point_id)
    return "Charger done"
