import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Coroutine

from ocpp.v201 import ChargePoint as Cp, call, enums
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
from elu.twin.charge_point.env import REDIS_HOSTNAME
from elu.twin.data.helpers import get_now
from elu.twin.charge_point.generator import generate_protocol

from ocpp.v16.enums import ChargePointStatus as Cps
from loguru import logger


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

    async def get_send_boot_notification(
        self, **kwargs
    ) -> call.BootNotificationPayload:
        await requests.update_charger_status(self.cpi.cid, Cps.available)

        return call.BootNotificationPayload(
            charging_station={"model": self.cpi.model, "vendor_name": self.cpi.vendor},
            reason=self.cpi.boot_reason,
        )

    async def send_status_notification(self, **kwargs):
        request = call.BootNotificationPayload(**kwargs)
        logger.warning(f"hi we get here: {request} ")
        await update_evse_and_connectors(self.cpi)

        for evse in self.cpi.evses:
            for connector in evse.connectors:
                call.StatusNotificationPayload(
                    timestamp=str(datetime.now(timezone.utc)),
                    connector_status=connector.status,
                    evse_id=evse.evseid,
                    connector_id=connector.connectorid,
                )

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

    async def start_transactions(
        self,
        evse_id: int,
        connector_id: int,
        id_tag: str,
        initial_soc: float,
        battery: float,
        delay_between_actions,
    ):
        transaction_id = self.generate_transaction_id(evse_id, connector_id)
        start = call.TransactionEventPayload(
            event_type=enums.TransactionEventType.started,
            timestamp=get_now(),
            trigger_reason=enums.TriggerReasonType.authorized,
            seq_no=0,
            id_token=asdict(IdTokenType(id_token=id_tag, type=enums.IdTokenType.local)),
            transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
            evse=asdict(EVSEType(id=evse_id, connector_id=connector_id)),
        )
        await self.send_transaction_event(**asdict(start))

        for i in range(10):
            event = call.TransactionEventPayload(
                event_type=enums.TransactionEventType.updated,
                timestamp=get_now(),
                trigger_reason=enums.TriggerReasonType.meter_value_periodic,
                transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
                seq_no=i + 1,
                evse=asdict(EVSEType(id=evse_id, connector_id=connector_id)),
            )

            await self.send_transaction_event(**asdict(event))
            await asyncio.sleep(5)

        stop = call.TransactionEventPayload(
            event_type=enums.TransactionEventType.ended,
            timestamp=get_now(),
            trigger_reason=enums.TriggerReasonType.deauthorized,
            transaction_info=asdict(TransactionType(transaction_id=transaction_id)),
            seq_no=10 + 1,
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
            self.process_actions(),
            self.consume_actions_redis(REDIS_HOSTNAME, f"actions-{self.cpi.id}"),
        ]
