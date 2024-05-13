import asyncio
import logging

from ocpp.v201.enums import Action, RegistrationStatusType
from datetime import datetime, UTC

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on, after
from ocpp.v201 import ChargePoint as Cp
from ocpp.v201 import call_result

logging.basicConfig(level=logging.INFO)


def get_now(as_string: bool = True) -> datetime | str:
    now = datetime.now(UTC)
    if as_string:
        return now.isoformat()
    return now


class ChargePoint(Cp):
    @on(Action.BootNotification)
    def on_boot_notification(self, charging_station, reason, **kwargs):
        return call_result.BootNotificationPayload(
            current_time=get_now(),
            interval=10,
            status=RegistrationStatusType.accepted,
        )

    @on(Action.StatusNotification)
    def on_status_notification(self, timestamp, connector, evse_id, connector_id):
        return call_result.StatusNotificationPayload()

    @on(Action.Heartbeat)
    def on_heartbeat(self):
        return call_result.HeartbeatPayload(current_time=get_now())

    @on(Action.TransactionEvent)
    def on_transaction_event(
        self, event_type, trigger_reason, transaction_info, **kwargs
    ):
        return call_result.TransactionEventPayload()


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
        on_connect, "0.0.0.0", 9001, subprotocols=["ocpp2.0.1"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
