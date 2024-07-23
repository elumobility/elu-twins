from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from ocpp.messages import Call, CallResult
from ocpp.v16 import ChargePoint, call
from ocpp.v16.enums import Action

from elu.twin.charge_point.charge_point.v16.charge_point import (
    ChargePoint as CpV16,
)
from elu.twin.data.schemas.charge_point import OutputChargePoint


@pytest.fixture
def output_charge_point():
    cp = OutputChargePoint()
    return cp


@pytest.fixture
def cp(ws):
    cpi = output_charge_point()
    cp = CpV16(cpi.cid, ws)
    return cp


@pytest.fixture
def boot_notification_call():
    return Call(
        unique_id="1",
        action=Action.BootNotification,
        payload={
            "chargePointVendor": "Alfen BV",
            "chargePointModel": "ICU Eve Mini",
            "firmwareVersion": "#1:3.4.0-2990#N:217H;1.0-223",
        },
    ).to_json()
