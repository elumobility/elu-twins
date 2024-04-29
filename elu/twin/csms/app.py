import asyncio
import logging
import random

from ocpp.v16.datatypes import IdTagInfo

from elu.twin.data.helpers import get_now

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v16 import ChargePoint as Cp
from ocpp.v16 import call_result
from ocpp.v16.enums import (
    Action,
    RegistrationStatus,
    AuthorizationStatus,
    DataTransferStatus,
    GenericStatus,
    ConfigurationStatus,
    RemoteStartStopStatus,
    ReservationStatus,
    CancelReservationStatus,
    TriggerMessageStatus,
    UnlockStatus,
    ResetStatus,
)

logging.basicConfig(level=logging.INFO)


class ChargePoint(Cp):
    @on(Action.BootNotification)
    def on_boot_notification(
        self, charge_point_vendor: str, charge_point_model: str, **kwargs
    ):
        return call_result.BootNotificationPayload(
            current_time=get_now(),
            interval=10,
            status=RegistrationStatus.accepted,
        )

    @on(Action.Heartbeat)
    def on_heartbeat(self):
        return call_result.HeartbeatPayload(current_time=get_now())

    @on(Action.StatusNotification)
    def on_status_notification(self, **kwargs):
        return call_result.StatusNotificationPayload()

    @on(Action.MeterValues)
    def on_meter_values(self, **kwargs):
        return call_result.MeterValuesPayload()

    @on(Action.StartTransaction)
    def on_start_transaction(self, connector_id, id_tag, meter_start, timestamp):
        transaction_id = random.randint(0, 10000000)
        return call_result.StartTransactionPayload(
            transaction_id=transaction_id,
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted),
        )

    @on(Action.StopTransaction)
    def on_stop_transaction(self, **kwargs):
        return call_result.StopTransactionPayload(
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted)
        )

    @on(Action.Authorize)
    def on_authorize(self, id_tag):
        return call_result.AuthorizePayload(
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted)
        )

    @on(Action.DataTransfer)
    def on_data_transfer(self, vendor_id, message_id, data):
        return call_result.DataTransferPayload(status=DataTransferStatus.accepted)

    @on(Action.DiagnosticsStatusNotification)
    def on_diagnostics_status_notification(self, status):
        return call_result.DiagnosticsStatusNotificationPayload()

    @on(Action.FirmwareStatusNotification)
    def on_firmware_status_notification(self, status):
        return call_result.FirmwareStatusNotificationPayload()

    @on(Action.LogStatusNotification)
    def on_log_status_notification(self, status):
        return call_result.LogStatusNotificationPayload()

    @on(Action.SecurityEventNotification)
    def on_security_event_notification(self, status):
        return call_result.SecurityEventNotificationPayload()

    @on(Action.SignCertificate)
    def on_sign_certificate(self, certificate_type, certificate):
        return call_result.SignCertificatePayload(status=GenericStatus.accepted)

    @on(Action.GetConfiguration)
    def on_get_configuration(self, key):
        return call_result.GetConfigurationPayload(
            configuration_key=key, unknown_key=[]
        )

    @on(Action.ChangeConfiguration)
    def on_change_configuration(self, key, value):
        return call_result.ChangeConfigurationPayload(
            status=ConfigurationStatus.accepted
        )

    @on(Action.RemoteStartTransaction)
    def on_remote_start_transaction(self, connector_id, id_tag):
        return call_result.RemoteStartTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )

    @on(Action.RemoteStopTransaction)
    def on_remote_stop_transaction(self, transaction_id):
        return call_result.RemoteStopTransactionPayload(
            status=RemoteStartStopStatus.accepted
        )

    @on(Action.ReserveNow)
    def on_reserve_now(self, connector_id, expiry_date, id_tag, reservation_id):
        return call_result.ReserveNowPayload(status=ReservationStatus.accepted)

    @on(Action.CancelReservation)
    def on_cancel_reservation(self, reservation_id):
        return call_result.CancelReservationPayload(
            status=CancelReservationStatus.accepted
        )

    @on(Action.TriggerMessage)
    def on_trigger_message(self, requested_message):
        return call_result.TriggerMessagePayload(status=TriggerMessageStatus.accepted)

    @on(Action.UnlockConnector)
    def on_unlock_connector(self, connector_id):
        return call_result.UnlockConnectorPayload(status=UnlockStatus.unlocked)

    @on(Action.Reset)
    def on_reset(self, type):
        return call_result.ResetPayload(status=ResetStatus.accepted)


async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports  %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    cp = ChargePoint(charge_point_id, websocket)

    await cp.start()


async def main():
    server = await websockets.serve(
        on_connect, "0.0.0.0", 9000, subprotocols=["ocpp1.6"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
