import asyncio
import json
from asyncio import Queue, Task
from typing import Coroutine

import redis
from loguru import logger
from sqlmodel import SQLModel

from elu.twin.charge_point import requests
from elu.twin.charge_point.charge_point.models.charge_point import (
    actions,
)
from elu.twin.charge_point.env import REDIS_HOSTNAME, REDIS_DB_ACTIONS, REDIS_PORT
from elu.twin.data.enums import PowerType, is_dc, ConnectorStatus, EvseStatus
from elu.twin.data.schemas.charge_point import OutputChargePoint as Cpi
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.transaction import (
    RedisRequestStartTransaction,
    RedisRequestStopTransaction,
)


class ChargePointConsumer:
    def __init__(self):
        self.cpi: Cpi | None = None
        self.actions_queue: Queue = Queue()
        self.actions_set: set[Task] = set()

    async def update_vehicle_soc(self, vid: Index, soc: float):
        await requests.update_vehicle_soc(vid=vid, soc=soc)

    async def update_connector_status(
        self, evse: int, connector: int, status: ConnectorStatus
    ):
        """

        :param evse:
        :param connector:
        :param status:
        """
        self.cpi.evses[evse].connectors[connector].status = status
        await requests.update_connector_status(
            self.cpi.evses[evse].connectors[connector].id, status
        )
        await asyncio.sleep(1)

    async def update_evse_status(
        self, evse: int, status: EvseStatus, active_connector: int | None = None
    ):
        """

        :param evse:
        :param status:
        :param active_connector:
        """
        self.cpi.evses[evse].status = status
        self.cpi.evses[evse].active_connector_id = active_connector
        evse_id = self.cpi.evses[evse].id
        await requests.update_evse_status(
            evse_id=evse_id, status=status, active_connector=active_connector
        )
        await asyncio.sleep(1)

    def get_connector_meter_value(self, evse_id: int, connector_id: int):
        """

        :param evse_id:
        :param connector_id:
        :return:
        """
        return int(self.cpi.evses[evse_id].connectors[connector_id].meter_value)

    def update_connector_meter_value(
        self, evse_id: int, connector_id: int, add_energy: float, soc: float
    ):
        """

        :param evse_id:
        :param connector_id:
        :param add_energy:
        :param soc:
        :return:
        """
        self.cpi.evses[evse_id - 1].connectors[
            connector_id - 1
        ].session_energy += add_energy
        self.cpi.evses[evse_id - 1].connectors[
            connector_id - 1
        ].meter_value += add_energy
        self.cpi.evses[evse_id - 1].connectors[connector_id - 1].soc = soc
        return self.get_connector_meter_value(evse_id, connector_id)

    async def get_connector_power(
        self, evse_id: int, connector_id: int, soc: int, vid: Index
    ):
        """

        :param evse_id:
        :param connector_id:
        :param soc:
        :return:
        """
        if soc >= 100:
            power = 0
        else:
            connector_type = (
                self.cpi.evses[evse_id].connectors[connector_id].connector_type
            )
            power_type = PowerType.dc if is_dc(connector_type) else PowerType.ac
            power = await requests.get_charging_rate(
                vid=vid, soc=soc, power_type=power_type
            )
            power_offered = (
                self.cpi.evses[evse_id].connectors[connector_id].power_exported
            )
            power = min(power_offered, power) if power_offered else power

        voltage = self.cpi.evses[evse_id].connectors[connector_id].voltage
        current = power / voltage * 1000
        self.cpi.evses[evse_id].connectors[connector_id].power_imported = power
        self.cpi.evses[evse_id].connectors[connector_id].current_imported = current

        return power

    async def add_action_to_queue(self, obj):
        """

        :param obj:
        """
        await self.actions_queue.put(obj)

    async def process_actions(self):
        """
        Process actions
        """
        while True:
            obj = await self.actions_queue.get()
            if isinstance(obj, RedisRequestStartTransaction):
                start_transaction: RedisRequestStartTransaction = obj
                self.actions_queue.task_done()
                task = asyncio.create_task(
                    self.start_transaction(**start_transaction.dict())
                )
                self.actions_set.add(task)
                task.add_done_callback(self.actions_set.discard)
            elif isinstance(obj, RedisRequestStopTransaction):
                stop_transaction: RedisRequestStopTransaction = obj
                self.actions_queue.task_done()
                task = asyncio.create_task(
                    self.stop_transaction(**stop_transaction.dict())
                )
                self.actions_set.add(task)
                task.add_done_callback(self.actions_set.discard)
            #            elif isinstance(obj, Disconnect):
            #                self.actions_queue.task_done()
            #                task = asyncio.create_task(
            #                    self.connect_disconnect(mode=ChargePointStatus.unavailable)
            #                )
            #                self.actions_set.add(task)
            #                task.add_done_callback(self.actions_set.discard)
            else:
                logger.warning(f"unknown action: {obj}")

    @logger.catch
    async def consume_actions_redis(self, channel: str):
        """

        :param host:
        :param channel:
        """
        r = redis.Redis(
            host=REDIS_HOSTNAME,
            port=REDIS_PORT,
            db=REDIS_DB_ACTIONS,
            decode_responses=True,
        )
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe(channel)
        while True:
            message = p.get_message()
            if message:
                try:
                    data = message.get("data")
                    obj = json.loads(data)
                    action_name: SQLModel = obj.get("name")
                    if action_name in actions:
                        model: SQLModel = actions.get(action_name)
                        if model:
                            action = model.model_validate(obj)
                            await self.add_action_to_queue(action)
                        else:
                            logger.warning(
                                f"model not found: {action_name} not in {actions}"
                            )
                    else:
                        logger.warning(f"action not found: {data}")
                except:
                    logger.error(f"error parsing: {message}")
                    await asyncio.sleep(3)
            #                    p = r.pubsub()
            #                    p.subscribe(channel)
            await asyncio.sleep(1)
