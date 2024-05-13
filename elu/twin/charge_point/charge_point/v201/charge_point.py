import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Coroutine
from elu.twin.data.enums import VehicleStatus
from elu.twin.data.schemas.common import Index
from ocpp.v201 import ChargePoint as Cp, call, enums, call_result
from ocpp.v201 import call_result
from ocpp.v201.datatypes import (
    TransactionType,
    IdTokenType,
    EVSEType,
    MeterValueType,
    SampledValueType,
)

from ocpp.v201.enums import (
    Action,
    ReadingContextType,
    MeasurandType,
    LocationType,
    UnitOfMeasureType,
)

from elu.twin.charge_point import requests
from elu.twin.charge_point.charge_point.charge_point_consumer import (
    ChargePointConsumer,
)
from elu.twin.charge_point.charge_point.helpers import update_evse_and_connectors
from elu.twin.charge_point.env import REDIS_HOSTNAME, VID_PREFFIX
from elu.twin.data.helpers import get_now
from elu.twin.charge_point.generator import generate_protocol

from ocpp.v16.enums import ChargePointStatus as Cps
from loguru import logger
from ocpp.routing import on, after
import inspect


class ChargePointBase(Cp, ChargePointConsumer):
    def __init__(self, *args, **kwargs):
        Cp.__init__(self, *args, **kwargs)
        ChargePointConsumer.__init__(self)


generate_protocol(
    base=ChargePointBase, actions=Action, call=call, call_result=call_result
)


class ChargePoint(ChargePointBase):
    def __init__(self, *args, **kwargs):
        ChargePointBase.__init__(self, *args, **kwargs)

    async def get_send_heartbeat(self, interval=30):
        request = call.HeartbeatPayload()
        while True:
            await self.call(request)
            await asyncio.sleep(interval)

    async def get_send_boot_notification(
        self, **kwargs
    ) -> call.BootNotificationPayload:
        await requests.update_charger_status(self.cpi.cid, Cps.available)

        request = call.BootNotificationPayload(
            charging_station={"model": self.cpi.model, "vendor_name": self.cpi.vendor},
            reason=self.cpi.boot_reason,
        )
        return request

    async def get_after_boot_notification(self, response):
        await update_evse_and_connectors(self.cpi)
        for evse in self.cpi.evses:
            for connector in evse.connectors:
                # print(f"hi: {connector.id}")
                request = call.StatusNotificationPayload(
                    timestamp=str(datetime.now(timezone.utc)),
                    connector_status=connector.status,
                    evse_id=evse.evseid,
                    connector_id=connector.connectorid,
                )
                # re = await self.call(request)
                print("get after:", request)
                # print("\n 1 get after:", re)
        return response

    async def get_send_status_notification(self, **kwargs):
        # request = call.BootNotificationPayload(**kwargs)
        logger.warning("hi we get here:")
        # await update_evse_and_connectors(self.cpi)
        evse = self.cpi.evses[0]
        connector = evse.connectors[0]
        return call.StatusNotificationPayload(
            timestamp=str(datetime.now(timezone.utc)),
            connector_status=connector.status,
            evse_id=evse.evseid,
            # connector_id=connector.connectorid,
        )
        # for evse in self.cpi.evses:
        #     for connector in evse.connectors:

    def generate_transaction_id(self, evse_id: int, connector_id: int):
        return f"{evse_id}-{connector_id}-{str(datetime.now().timestamp()).replace('.', '-')}"

    async def get_meter_value_event(self, power, energy, soc):
        """

        :param power:
        :param energy:
        :param soc:
        :return:
        """
        return [
            MeterValueType(
                timestamp=get_now(),
                sampled_value=[
                    SampledValueType(
                        value=energy,
                        context=ReadingContextType.sample_periodic,
                        measurand=MeasurandType.energy_active_import_register,
                        location=LocationType.cable,
                        unit_of_measure=UnitOfMeasureType.wh,
                    ),
                    SampledValueType(
                        value=power,
                        context=ReadingContextType.sample_periodic,
                        measurand=MeasurandType.power_active_import,
                        location=LocationType.cable,
                        unit_of_measure=UnitOfMeasureType.w,
                    ),
                    SampledValueType(
                        value=soc,
                        context=ReadingContextType.sample_periodic,
                        measurand=MeasurandType.soc,
                        location=LocationType.ev,
                        unit_of_measure=UnitOfMeasureType.percent,
                    ),
                ],
            )
        ]

    async def _get_transaction_info(self, transaction_id: Index):
        transaction = await requests.get_transaction(transaction_id)

        # Get vehicle info
        vehicle = await requests.get_vehicle(transaction.vehicle_id)
        await requests.update_vehicle_status(vehicle.id, VehicleStatus.charging)

        # Get evse and connectors indexes
        eix, cix = next(
            (eix, cix)
            for eix, evse in enumerate(self.cpi.evses)
            for cix, connector in enumerate(evse.connectors)
            if connector.id == transaction.connector_id
        )
        return vehicle, eix, cix

    async def start_transaction(
        self,
        name: str,
        transaction_id: Index,
        delay_between_actions: int = 1,
    ):
        logger.warning("whatss")
        vehicle, evse_id, connector_id = await self._get_transaction_info(
            transaction_id=transaction_id
        )
        id_tag = f"{VID_PREFFIX}{vehicle.id_tag_suffix}"
        i = 0
        start = call.TransactionEventPayload(
            event_type=enums.TransactionEventType.started,
            timestamp=get_now(),
            trigger_reason=enums.TriggerReasonType.authorized,
            seq_no=i,
            id_token=asdict(IdTokenType(id_token=id_tag, type=enums.IdTokenType.local)),
            transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
            evse=asdict(EVSEType(id=evse_id, connector_id=connector_id)),
        )
        await self.send_transaction_event(**asdict(start))

        charge = True
        interval = 5

        while charge:
            print("do we even get here")
            i += 1
            event = call.TransactionEventPayload(
                event_type=enums.TransactionEventType.updated,
                timestamp=get_now(),
                trigger_reason=enums.TriggerReasonType.meter_value_periodic,
                transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
                seq_no=i,
                evse=asdict(EVSEType(id=evse_id, connector_id=connector_id)),
                meter_value=self.get_meter_value_event(power=10, soc=10, energy=10),
            )
            await self.send_transaction_event(**asdict(event))
            print("do we even get here11")
            await asyncio.sleep(interval)

        stop = call.TransactionEventPayload(
            event_type=enums.TransactionEventType.ended,
            timestamp=get_now(),
            trigger_reason=enums.TriggerReasonType.deauthorized,
            transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
            seq_no=i + 1,
            evse=asdict(EVSEType(id=evse_id, connector_id=connector_id)),
        )

        await self.send_transaction_event(**asdict(stop))

    def get_processes(self) -> list[Coroutine]:
        """

        :return:
        """
        return [
            self.start(),
            self.send_boot_notification(),
            self.send_heartbeat(),
            # self.send_status_notification(),
            self.process_actions(),
            self.consume_actions_redis(f"actions-{self.cpi.id}"),
        ]
