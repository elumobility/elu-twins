import asyncio
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Coroutine, Tuple

from elu.twin.data.enums import (
    AuthorizationStatus,
    ConnectorQueuedActions,
    EvseStatus,
    ConnectorStatus,
    VehicleStatus,
    TransactionStatus,
)
from elu.twin.data.helpers import get_now
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.connector import UpdateConnector
from elu.twin.data.schemas.ocpp_configuration import (
    OutputOcppConfigurationV16,
    is_read_only,
    OcppConfigurationV16Update,
)
from elu.twin.data.schemas.schedule import Schedule
from elu.twin.data.schemas.transaction import (
    RequestStopTransaction,
    RequestStartTransaction,
    UpdateTransaction,
)
from ocpp.v16 import ChargePoint as Cp, call
from ocpp.v16 import call_result
from ocpp.v16.datatypes import (
    SampledValue,
    MeterValue,
    ChargingProfile,
    ChargingSchedule,
    AuthorizationData,
    IdTagInfo,
)
from ocpp.v16.enums import (
    Action,
    ChargePointErrorCode,
    Reason,
    RemoteStartStopStatus,
    UnitOfMeasure,
    Location,
    Measurand,
    ValueFormat,
    ReadingContext,
    ConfigurationStatus,
    AvailabilityStatus,
    ClearCacheStatus,
    RegistrationStatus,
    ReservationStatus,
    UnlockStatus,
    ChargingProfileStatus,
    GetCompositeScheduleStatus,
    ChargingRateUnitType,
    ResetStatus,
    ClearChargingProfileStatus,
    UpdateType,
    UpdateStatus,
    CancelReservationStatus,
    ChargePointStatus,
)
from pydantic.tools import parse_obj_as

from elu.twin.charge_point import requests
from elu.twin.charge_point.charge_point.charge_point_consumer import (
    ChargePointConsumer,
)
from elu.twin.charge_point.charge_point.models.charge_point import (
    Reservation,
    AssignedChargingProfile,
)

from elu.twin.charge_point.env import VID_PREFFIX
from elu.twin.charge_point.generator import generate_protocol


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
        self.ocpp_configuration: OutputOcppConfigurationV16 | None = None

    async def update_to_connect(self):
        self.cpi.status = ChargePointStatus.available
        await requests.update_charger_status(self.cpi.id, self.cpi.status)
        for evse in self.cpi.evses:
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

    async def get_on_reset(self, **kwargs):
        request = call.ResetPayload(**kwargs)
        if self.cpi.reset:
            return call_result.ResetPayload(status=ResetStatus.rejected)
        self.cpi.reset = request.type
        return call_result.ResetPayload(status=ResetStatus.accepted)

    async def get_on_get_local_list_version(self, **kwargs):
        return call_result.GetLocalListVersionPayload(
            list_version=self.cpi.authorization_list_version
        )

    async def get_meter_value_event(self, power, energy, soc):
        """

        :param power:
        :param energy:
        :param soc:
        :return:
        """
        return [
            MeterValue(
                timestamp=get_now(),
                sampled_value=[
                    SampledValue(
                        value=str(energy),
                        context=ReadingContext.sample_periodic,
                        format=ValueFormat.raw,
                        measurand=Measurand.energy_active_import_register,
                        location=Location.cable,
                        unit=UnitOfMeasure.wh,
                    ),
                    SampledValue(
                        value=str(power),
                        context=ReadingContext.sample_periodic,
                        format=ValueFormat.raw,
                        measurand=Measurand.power_active_import,
                        location=Location.cable,
                        unit=UnitOfMeasure.w,
                    ),
                    SampledValue(
                        value=str(soc),
                        context=ReadingContext.sample_periodic,
                        format=ValueFormat.raw,
                        measurand=Measurand.soc,
                        location=Location.ev,
                        unit=UnitOfMeasure.percent,
                    ),
                ],
            )
        ]

    def get_composeite_schedule(
        self, connector_id: int, duration: int, charging_rate_unit: ChargingRateUnitType
    ) -> ChargingSchedule:
        schedule = Schedule()
        charging_profiles = []
        for charging_profile in self.cpi.charging_profiles:
            if charging_profile.connector_0:
                charging_profiles.append(charging_profile.charging_profile)
            elif connector_id == self._get_ocpp_connector_id(
                charging_profile.evse_id, charging_profile.connector_id
            ):
                charging_profiles.append(charging_profile.charging_profile)

        composite_schedule = schedule.from_ocpp_charging_profiles(
            profiles=charging_profiles,
            duration=duration,
            charging_rate_unit=charging_rate_unit,
        )
        return composite_schedule

    async def get_on_get_composite_schedule(self, **kwargs):
        request = call.GetCompositeSchedulePayload(**kwargs)
        schedule = self.get_composeite_schedule(**asdict(request))
        return call_result.GetCompositeSchedulePayload(
            status=GetCompositeScheduleStatus.accepted,
            connector_id=request.connector_id,
            schedule_start=schedule.start_schedule,
            charging_schedule=asdict(schedule),
        )

    async def get_on_set_charging_profile(self, **kwargs):
        response = call.SetChargingProfilePayload(**kwargs)
        charging_profile = parse_obj_as(ChargingProfile, response.cs_charging_profiles)
        if response.connector_id == 0:
            assigned_charging_profile = AssignedChargingProfile(
                connector_0=True, charging_profile=charging_profile
            )
        else:
            evse_id, connector_id = self._get_evse_and_connector_id(
                response.connector_id
            )
            assigned_charging_profile = AssignedChargingProfile(
                connector_0=False,
                connector_id=connector_id,
                evse_id=evse_id,
                charging_profile=charging_profile,
            )
        self.cpi.add_charging_profile(assigned_charging_profile)
        return call_result.SetChargingProfilePayload(
            status=ChargingProfileStatus.accepted
        )

    async def get_on_remote_stop_transaction(self, **kwargs):
        request = call.RemoteStopTransactionPayload(**kwargs)
        connector = next(
            (
                connector
                for evse in self.cpi.evses
                for connector in evse.connectors
                if connector.transactionid == request.transaction_id
            ),
            None,
        )
        if connector:
            message = await requests.stop_transaction(
                transaction=RequestStopTransaction(
                    transaction_id=request.transaction_id
                ),
                user_id=self.cpi.user_id,
            )
            if message:
                return call_result.RemoteStopTransactionPayload(
                    status=RemoteStartStopStatus.accepted
                )
        return call_result.RemoteStopTransactionPayload(
            status=RemoteStartStopStatus.rejected
        )

    async def get_on_remote_start_transaction(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        request = call.RemoteStartTransactionPayload(**kwargs)
        evse_id, connector_id = next(
            (
                (eix, cix)
                for eix, evse in enumerate(self.cpi.evses)
                for cix, connector in enumerate(evse.connectors)
                if connector.connectorid == request.connector_id
            ),
            (None, None),
        )
        if (evse_id is None) or (connector_id is None):
            logging.warning(f"Connector {request.connector_id} not found")
            return call_result.RemoteStartTransactionPayload(
                status=RemoteStartStopStatus.rejected
            )
        if (self.cpi.evses[evse_id].status != EvseStatus.available) or (
            self.cpi.evses[evse_id].connectors[connector_id].status
            != ConnectorStatus.available
        ):
            logging.warning(f"Connector {request.connector_id} not available")
            return call_result.RemoteStartTransactionPayload(
                status=RemoteStartStopStatus.rejected
            )

        transaction = await requests.start_transaction(
            transaction=RequestStartTransaction(
                connector_id=self.cpi.evses[evse_id].connectors[connector_id].id
            ),
            user_id=self.cpi.user_id,
        )
        if transaction is None:
            logging.warning(f"Transaction not started")
            return call_result.RemoteStartTransactionPayload(
                status=RemoteStartStopStatus.rejected
            )
        return call_result.RemoteStartTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )

    async def get_on_get_configuration(self, **kwargs):
        request = call.GetConfigurationPayload(**kwargs)
        keys, unknown_keys = self.ocpp_configuration.get_list_of_keys(request.key)
        return call_result.GetConfigurationPayload(
            configuration_key=keys, unknown_key=unknown_keys
        )

    async def get_on_change_configuration(self, **kwargs):
        try:
            request = call.ChangeConfigurationPayload(**kwargs)
            if is_read_only(request.key):
                return call_result.ChangeConfigurationPayload(
                    status=ConfigurationStatus.rejected
                )
            self.ocpp_configuration.set_value(key=request.key, value=request.value)
            update_configuration = OcppConfigurationV16Update()
            setattr(
                update_configuration,
                request.key,
                self.ocpp_configuration.model_dump()[request.key],
            )
            _ = await requests.update_chager_point_configuration(
                self.ocpp_configuration.id, update_configuration
            )
            return call_result.ChangeConfigurationPayload(
                status=ConfigurationStatus.accepted
            )
        except Exception as e:
            logging.error(e)
            return call_result.ChangeConfigurationPayload(
                status=ConfigurationStatus.rejected
            )

    def _get_evse_and_connector_id(self, ocpp_connector_id: int) -> Tuple[int, int]:
        cumulative = 0
        cumulatives = []
        for i, evse in enumerate(self.cpi.evses):
            nc = len(evse.connectors)
            cumulatives.append(cumulative + nc)
            cumulative += nc
        for i, c in enumerate(cumulatives):
            if i == 0:
                if ocpp_connector_id <= c:
                    return i + 1, ocpp_connector_id
            else:
                if cumulatives[i - 1] < ocpp_connector_id <= cumulatives[i]:
                    return i + 1, ocpp_connector_id - cumulatives[i - 1]

        return ocpp_connector_id, ocpp_connector_id

    def _get_ocpp_connector_id(self, evse_id: int, connector_id: int) -> int:
        ocpp_connector_id = 0
        for evse in self.cpi.evses:
            if evse.evse_id == evse_id:
                ocpp_connector_id += connector_id
                return ocpp_connector_id
            else:
                ocpp_connector_id += len(evse.connectors)

    async def get_on_change_availability(self, **kwargs):
        request = call.ChangeAvailabilityPayload(**kwargs)
        evse_id, connector_id = self._get_evse_and_connector_id(request.connector_id)
        self.cpi.evses[evse_id - 1].connectors[
            connector_id - 1
        ].availability = request.type
        # TODO: update in endpoint
        # TODO: check if transition is valid
        return call_result.ChangeAvailabilityPayload(status=AvailabilityStatus.accepted)

    async def get_on_clear_cache(self, **kwargs):
        self.cpi.authorization_cache = []
        # TODO        await requests.clear_cache(self.cpi.user_id, self.cpi.cid)
        return call_result.ClearCachePayload(status=ClearCacheStatus.accepted)

    def _updated_authorization_data(
        self, auth_list: list[AuthorizationData]
    ) -> list[AuthorizationData] | None:

        _id_tags = {auth.id_tag for auth in self.cpi.authorization_list}
        _update_tags = {auth.id_tag for auth in auth_list}
        if not _update_tags.issubset(_id_tags):
            return None
        _update_dict = {auth.id_tag: auth for auth in auth_list}
        new_list = [
            (_update_dict.get(auth.id_tag) if _update_dict.get(auth.id_tag) else auth)
            for auth in self.cpi.authorization_list
        ]
        if len(new_list) > self.ocpp_configuration.LocalAuthListMaxLength:
            return None
        new_list1 = [AuthorizationData(**x) for x in new_list]
        return new_list1

    async def get_on_send_local_list(self, **kwargs):
        if not self.ocpp_configuration.LocalAuthListEnabled:
            return call_result.SendLocalListPayload(status=UpdateStatus.not_supported)
        response = call.SendLocalListPayload(**kwargs)
        self.cpi.authorization_list_version = response.list_version
        if response.update_type == UpdateType.differential:
            _list: list[AuthorizationData] = response.local_authorization_list
            updated_list = self._updated_authorization_data(_list)
            if updated_list is None:
                return call_result.SendLocalListPayload(status=UpdateStatus.failed)
            self.cpi.local_auth_list = updated_list
        else:
            if (
                len(response.local_authorization_list)
                > self.ocpp_configuration.LocalAuthListMaxLength
            ):
                return call_result.SendLocalListPayload(status=UpdateStatus.failed)
            else:
                self.cpi.local_auth_list = [
                    AuthorizationData(**x) for x in response.local_authorization_list
                ]

        self.cpi.authorization_list_version = response.list_version
        return call_result.SendLocalListPayload(status=UpdateStatus.accepted)

    async def get_on_cancel_reservation(self, **kwargs):
        response = call.CancelReservationPayload(**kwargs)
        for i in range(len(self.cpi.reservations)):
            if self.cpi.reservations[i].reservation_id == response.reservation_id:
                del self.cpi.reservations[i]
                # TODO
                #                await requests.cancel_reservation(
                #                    self.cpi.user_id, self.cpi.cid, response.reservation_id
                #                )
                return call_result.CancelReservationPayload(
                    status=CancelReservationStatus.accepted
                )
        return call_result.CancelReservationPayload(
            status=CancelReservationStatus.rejected
        )

    async def get_on_clear_charging_profile(self, **kwargs):
        request = call.ClearChargingProfilePayload(**kwargs)
        keep_profiles = []
        for cp in self.cpi.charging_profiles:
            by_id = ~(
                cp.charging_profile.charging_profile_id == request.id
                if request.id
                else False
            )
            # TODO: implement other filters
            if request.connector_id:
                by_connector = ~(
                    request.connector_id == 0
                    or request.connector_id
                    == self._get_ocpp_connector_id(cp.evse_id, cp.connector_id)
                )
            else:
                by_connector = True
            by_purpose = ~(
                cp.charging_profile.charging_profile_purpose
                == request.charging_profile_purpose
                if request.charging_profile_purpose
                else False
            )
            by_stack = ~(
                cp.charging_profile.stack_level == request.stack_level
                if request.stack_level
                else False
            )
            if by_id and by_connector and by_purpose and by_stack:
                keep_profiles.append(cp)
        self.cpi.charging_profiles = keep_profiles
        #  TODO: update list in end point
        return call_result.ClearChargingProfilePayload(
            status=ClearChargingProfileStatus.accepted
        )

    async def get_on_diagnostics_status_notification(self, **kwargs):
        _ = call.DiagnosticsStatusNotificationPayload(**kwargs)
        return call_result.DiagnosticsStatusNotificationPayload()

    async def stop_transaction(
        self,
        name: str,
        transaction_id: Index,
    ):
        """

        :param name:
        :param transaction_id:
        """
        transaction = await requests.get_transaction(transaction_id)
        for eix, evse in enumerate(self.cpi.evses):
            for cix, connector in enumerate(evse.connectors):
                if connector.id == transaction.connector_id:
                    self.cpi.evses[eix].connectors[
                        cix
                    ].queued_action = ConnectorQueuedActions.stop_charging

    async def get_on_unlock_connector(self, **kwargs):
        request = call.UnlockConnectorPayload(**kwargs)
        evse_id, connector_id = self._get_evse_and_connector_id(
            ocpp_connector_id=request.connector_id
        )
        if self.cpi.evses[evse_id].connectors[connector_id].status in [
            ChargePointStatus.charging,
            ChargePointStatus.preparing,
            ChargePointStatus.finishing,
        ]:
            return call_result.UnlockConnectorPayload(status=UnlockStatus.unlocked)
        return call_result.UnlockConnectorPayload(status=UnlockStatus.unlocked)

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

    async def _set_preparing_state(
        self, eix: int, cix: int, ocpp_connector_id: int, delay_between_actions: int = 1
    ):
        await self.update_evse_status(
            evse=eix, status=EvseStatus.busy, active_connector=cix
        )
        await asyncio.sleep(delay_between_actions)

        # Update connector status
        preparing = call.StatusNotificationPayload(
            connector_id=ocpp_connector_id,
            error_code=ChargePointErrorCode.no_error,
            status=ChargePointStatus.preparing,
            timestamp=get_now(),
        )
        await self.send_status_notification(**asdict(preparing))
        await self.update_connector_status(eix, cix, ConnectorStatus.preparing)
        await asyncio.sleep(delay_between_actions)

    async def _try_authorize(
        self, id_tag: str, ocpp_connector_id: int, delay_between_actions: int = 1
    ):
        call_csms = True
        # Check if chargepoint can authorize id_tag locally
        logging.debug("are we getting here")
        if self.ocpp_configuration.LocalAuthListEnabled:
            print("\n dir: ", dir(self))
            if self.cpi.local_auth_list:
                print("\n local_auth_list: ", self.cpi.local_auth_list)
                auth_data = [x for x in self.cpi.local_auth_list if x.id_tag == id_tag]
                if (
                    auth_data
                    and auth_data[0].id_tag_info.status == AuthorizationStatus.accepted
                ):
                    call_csms = False

        if call_csms:
            authorize = call.AuthorizePayload(id_tag=id_tag)
            response_authorize: call_result.AuthorizePayload = (
                await self.send_authorize(**asdict(authorize))
            )
            print("response", response_authorize)

        # TODO Implement authorization in CSMS
        #        authorize = call.AuthorizePayload(id_tag=id_tag)
        #        response_authorize: call_result.AuthorizePayload = await self.send_authorize(
        #            **asdict(authorize)
        #        )
        #        if response_authorize.id_tag_info.get("status") != AuthorizationStatus.accepted:
        #            #  TO do fix when status is unathorized  and status is suspeneded
        #            unauthorized = call.StatusNotificationPayload(
        #                connector_id=connector_id,
        #                error_code=ChargePointErrorCode.no_error,
        #                status=ChargePointStatus.suspendedevse,
        #                timestamp=get_now(),
        #            )
        #            await self.send_status_notification(**asdict(unauthorized))
        #            await self.update_connector_status(evse_id, connector_id, ChargePointStatus.suspendedevse)
        #            await asyncio.sleep(delay_between_actions)
        #            available = call.StatusNotificationPayload(
        #                connector_id=ocpp_connector_id,
        #                error_code=ChargePointErrorCode.no_error,
        #                status=ChargePointStatus.available,
        #                timestamp=get_now(),
        #            )
        #            await self.send_status_notification(**asdict(available))
        #            await self.update_connector_status(evse_id, connector_id, ChargePointStatus.available)
        #            return None

        #        await asyncio.sleep(delay_between_actions)
        # Request start transaction
        # TODO: Implement reservation
        return None

    async def _try_to_start_transaction(
        self, ocpp_connector_id, id_tag, meter_start, reservation_id, transaction_id
    ) -> call_result.StartTransactionPayload:
        start = call.StartTransactionPayload(
            connector_id=ocpp_connector_id,
            id_tag=id_tag,
            timestamp=get_now(),
            meter_start=meter_start,
            reservation_id=reservation_id,
        )
        response_start: call_result.StartTransactionPayload = (
            await self.send_start_transaction(**asdict(start))
        )

        # TODO: Control refuse start session
        #        if reservation_id:
        #            self.cpi.delete_reservation(reservation_id)
        #            await requests.cancel_reservation(
        #                self.cpi.user_id, self.cpi.cid, reservation_id
        #            )

        _ = await requests.update_transaction(
            transaction_id,
            transaction_update=UpdateTransaction(
                status=TransactionStatus.accepted,
                transactionid=response_start.transaction_id,
            ),
        )
        return response_start

    async def _prepare_charging(
        self,
        eix: int,
        cix: int,
        initial_soc: float,
        ocpp_connector_id: int,
        id_tag: str,
        current_scale: int,
        transaction_id: Index,
        transactionid: int,
        delay_between_actions: int,
    ):
        self.cpi.evses[eix].connectors[cix].transactionid = transactionid
        self.cpi.evses[eix].connectors[cix].id_tag = id_tag
        self.cpi.evses[eix].connectors[cix].current_dc_power = self.cpi.maximum_dc_power
        self.cpi.evses[eix].connectors[cix].current_dc_current = int(
            current_scale * self.cpi.maximum_dc_power / self.cpi.voltage_dc
        )
        self.cpi.evses[eix].connectors[cix].current_dc_voltage = self.cpi.voltage_dc
        self.cpi.evses[eix].connectors[cix].current_energy = 0
        self.cpi.evses[eix].connectors[cix].soc = initial_soc
        connector_update = UpdateConnector(
            current_dc_power=self.cpi.maximum_dc_power,
            current_dc_current=int(self.cpi.maximum_dc_power / self.cpi.voltage_dc),
            current_dc_voltage=self.cpi.voltage_dc,
            current_energy=0,
            total_energy=self.cpi.evses[eix].connectors[cix].total_energy,
            soc=initial_soc,
            id_tag=id_tag,
            transactionid=transactionid,
        )
        await requests.update_connector_values(
            connector_id=self.cpi.evses[eix].connectors[cix].id,
            connector_update=connector_update,
        )

        await asyncio.sleep(delay_between_actions)
        charging = call.StatusNotificationPayload(
            connector_id=ocpp_connector_id,
            error_code=ChargePointErrorCode.no_error,
            status=ChargePointStatus.charging,
            timestamp=get_now(),
        )
        await self.send_status_notification(**asdict(charging))
        await self.update_connector_status(eix, cix, ConnectorStatus.charging)
        await asyncio.sleep(delay_between_actions)

        _ = await requests.update_transaction(
            transaction_id,
            transaction_update=UpdateTransaction(status=TransactionStatus.running),
        )

    async def _charging_cycle(
        self,
        eix,
        cix,
        meter_values_interval,
        initial_soc,
        battery,
        ocpp_connector_id,
        id_tag,
        response_start,
        vehicle,
        transactionid,
        current_scale,
    ):
        #            self.cpi.evses[eix].connectors[cix].current_dc_power = await self.get_connector_power(
        #                evse_id=eix, connector_id=cix, soc=self.cpi.evses[eix].connectors[cix].soc, vid=vehicle.id
        #            )
        self.cpi.evses[eix].connectors[cix].current_dc_power = (
            self.cpi.maximum_dc_power
            if self.cpi.evses[eix].connectors[cix].soc < 100
            else 0
        )
        add_energy = (
            self.cpi.evses[eix].connectors[cix].current_dc_power
            * (meter_values_interval / 3600.0)
            * 1000
        )
        self.cpi.evses[eix].connectors[cix].current_energy += add_energy
        self.cpi.evses[eix].connectors[cix].soc = min(
            100,
            int(
                initial_soc
                + self.cpi.evses[eix].connectors[cix].current_energy
                / 1000
                * 100
                / battery
            ),
        )
        self.cpi.evses[eix].connectors[cix].total_energy += add_energy
        list_meter_value = await self.get_meter_value_event(
            self.cpi.evses[eix].connectors[cix].current_dc_power,
            int(self.cpi.evses[eix].connectors[cix].total_energy),
            self.cpi.evses[eix].connectors[cix].soc,
        )
        meter_value = call.MeterValuesPayload(
            connector_id=ocpp_connector_id,
            transaction_id=response_start.transaction_id,
            meter_value=list_meter_value,
        )
        await self.send_meter_values(**asdict(meter_value))
        _ = await requests.update_transaction(
            transactionid,
            transaction_update=UpdateTransaction(
                energy=self.cpi.evses[eix].connectors[cix].current_energy,
            ),
        )
        connector_update = UpdateConnector(
            current_dc_power=self.cpi.evses[eix].connectors[cix].current_dc_power,
            current_dc_current=int(
                current_scale
                * self.cpi.evses[eix].connectors[cix].current_dc_power
                / self.cpi.voltage_dc
            ),
            current_dc_voltage=self.cpi.voltage_dc,
            current_energy=self.cpi.evses[eix].connectors[cix].current_energy,
            total_energy=self.cpi.evses[eix].connectors[cix].total_energy,
            soc=self.cpi.evses[eix].connectors[cix].soc,
            id_tag=id_tag,
            transactionid=response_start.transaction_id,
        )
        await requests.update_connector_values(
            self.cpi.evses[eix].connectors[cix].id, connector_update
        )
        await requests.update_vehicle_soc(
            vehicle.id, self.cpi.evses[eix].connectors[cix].soc
        )

    async def _continue_charging(self, eix, cix, meter_values_interval) -> bool:
        for i in range(meter_values_interval):
            if (
                self.cpi.evses[eix].connectors[cix].queued_action
                == ConnectorQueuedActions.stop_charging
            ):
                return False
            await asyncio.sleep(1)
        return True

    async def _finish_transaction(
        self,
        eix: int,
        cix: int,
        ocpp_connector_id: int,
        transactionid,
        id_tag: str,
        vehicle_id: Index,
        delay_between_actions: int,
    ):
        self.cpi.evses[eix].connectors[cix].queued_action = None
        await asyncio.sleep(delay_between_actions)

        stop = call.StopTransactionPayload(
            meter_stop=int(self.cpi.evses[eix].connectors[cix].total_energy),
            timestamp=get_now(),
            transaction_id=transactionid,
            reason=Reason.local,
            id_tag=id_tag,
        )
        _ = await self.send_stop_transaction(**asdict(stop))

        _ = await asyncio.sleep(delay_between_actions)
        finishing = call.StatusNotificationPayload(
            connector_id=ocpp_connector_id,
            error_code=ChargePointErrorCode.no_error,
            status=ChargePointStatus.finishing,
            timestamp=get_now(),
        )
        _ = await self.send_status_notification(**asdict(finishing))
        _ = await self.update_connector_status(eix, cix, ConnectorStatus.finishing)
        _ = await asyncio.sleep(delay_between_actions)
        available = call.StatusNotificationPayload(
            connector_id=ocpp_connector_id,
            error_code=ChargePointErrorCode.no_error,
            status=ChargePointStatus.available,
            timestamp=get_now(),
        )
        _ = await self.send_status_notification(**asdict(available))
        _ = await self.update_connector_status(eix, cix, ConnectorStatus.available)

        self.cpi.evses[eix].connectors[cix].transactionid = None
        self.cpi.evses[eix].connectors[cix].id_tag = None

        connector_update = UpdateConnector(
            current_dc_power=0,
            current_dc_current=0,
            current_dc_voltage=self.cpi.voltage_dc,
            current_energy=0,
            total_energy=self.cpi.evses[eix].connectors[cix].total_energy,
            soc=None,
            id_tag=None,
            transactionid=None,
            transaction_id=None,
        )
        _ = await requests.update_connector_values(
            self.cpi.evses[eix].connectors[cix].id, connector_update
        )

        _ = await self.update_evse_status(eix, status=EvseStatus.available)
        _ = await requests.update_vehicle_status(
            vehicle_id, VehicleStatus.ready_to_charge
        )
        _ = await requests.update_transaction(
            transactionid,
            transaction_update=UpdateTransaction(
                status=TransactionStatus.completed, end_time=get_now()
            ),
        )

    # async def update_local_list(self, id_tag_request: AuthorizationData):
    #     is_too_long = (
    #         len(self.local_auth_list) > self.ocpp_configuration.LocalAuthListMaxLength
    #     )
    #     for i, id_tag in enumerate(self.local_auth_list):
    #         if id_tag.id_tag == id_tag_request.id_tag:
    #             self.local_auth_list[i] = id_tag_request

    #     element = self.get_id_in_local_list(id_tag=id_tag_request.id_tag)

    async def start_transaction(
        self,
        name: str,
        transaction_id: Index,
        delay_between_actions: int = 1,
    ):
        """

        :param name:
        :param delay_between_actions:
        :return:
        """
        # Request access
        try:
            await asyncio.sleep(delay_between_actions)
            vehicle, eix, cix = await self._get_transaction_info(transaction_id)

            id_tag = f"{VID_PREFFIX}{vehicle.id_tag_suffix}"
            battery = vehicle.battery_capacity
            initial_soc = vehicle.soc
            ocpp_connector_id = self.cpi.evses[eix].connectors[cix].connectorid

            _ = await self._set_preparing_state(
                eix, cix, ocpp_connector_id, delay_between_actions
            )

            _ = await self._try_authorize(
                id_tag, ocpp_connector_id, delay_between_actions
            )

            # Start transaction
            reservation_id = None  # self.cpi.get_reservation_id(id_tag, connector_id)
            meter_start = int(self.cpi.evses[eix].connectors[cix].total_energy)

            response_start = await self._try_to_start_transaction(
                ocpp_connector_id, id_tag, meter_start, reservation_id, transaction_id
            )

            current_scale = 1000
            meter_values_interval = self.ocpp_configuration.MeterValueSampleInterval
            _ = await self._prepare_charging(
                eix,
                cix,
                initial_soc,
                ocpp_connector_id,
                id_tag,
                current_scale,
                transaction_id,
                response_start.transaction_id,
                delay_between_actions,
            )
            # Charging process
            charge = True
            while charge:
                _ = await self._charging_cycle(
                    eix,
                    cix,
                    meter_values_interval,
                    initial_soc,
                    battery,
                    ocpp_connector_id,
                    id_tag,
                    response_start,
                    vehicle,
                    response_start.transaction_id,
                    current_scale,
                )
                charge = await self._continue_charging(eix, cix, meter_values_interval)

            # Finishing charging sessions
            _ = await self._finish_transaction(
                eix,
                cix,
                ocpp_connector_id,
                response_start.transaction_id,
                id_tag,
                vehicle.id,
                delay_between_actions,
            )
        except Exception as e:
            logging.error(f"Error in transaction {transaction_id}: {e}")

    async def connect_charger(self):
        not_connected = True
        while not_connected:
            response: call_result.BootNotificationPayload = (
                await self.send_boot_notification()
            )
            if response.status == RegistrationStatus.accepted:
                await self.update_to_connect()
                not_connected = False
            await asyncio.sleep(response.interval)

    async def get_on_reserve_now(self, **kwargs):
        request = call.ReserveNowPayload(**kwargs)
        exp_date = datetime.strptime(request.expiry_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        if request.expiry_date > datetime.now().isoformat():
            self.cpi.reservations.append(
                Reservation(
                    connector_id=request.connector_id,
                    expiry_date=exp_date,
                    id_tag=request.id_tag,
                    reservation_id=request.reservation_id,
                    parent_id_tag=request.parent_id_tag,
                )
            )
            return call_result.ReserveNowPayload(status=ReservationStatus.accepted)
        return call_result.ReserveNowPayload(status=ReservationStatus.rejected)

    async def get_send_boot_notification(self) -> call.BootNotificationPayload:
        """

        :return:
        """
        #  Here update the status of the charger, evse and connectors

        return call.BootNotificationPayload(
            charge_point_model=self.cpi.model, charge_point_vendor=self.cpi.vendor
        )

    async def get_send_heartbeat(self, **kwargs):
        _ = await requests.update_heartbeat(self.cpi.id, get_now(as_string=False))
        return call.HeartbeatPayload()

    async def send_heartbeats_with_interval(self):
        while True:
            await asyncio.sleep(self.ocpp_configuration.HeartbeatInterval)
            await self.send_heartbeat()

    async def token_counter(self, interval: int = 60):
        while True:
            await asyncio.sleep(interval)
            await requests.consume_quota(
                self.cpi.quota_id, self.cpi.token_cost_per_minute
            )

    def get_processes(self) -> list[Coroutine]:
        """

        :return:
        """
        return [
            self.start(),
            self.connect_charger(),
            self.process_actions(),
            self.consume_actions_redis(f"actions-{self.cpi.id}"),
            self.send_heartbeats_with_interval(),
            self.token_counter(),
        ]
