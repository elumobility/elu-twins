import asyncio
import json
from unittest import mock

import pytest

from ocpp.exceptions import FormatViolationError, GenericError
from ocpp.messages import CallError
from ocpp.routing import after, create_route_map, on
from ocpp.v16 import ChargePoint, call, call_result
from ocpp.v16.enums import Action


@pytest.mark.asyncio
@on(Action.GetLocalListVersion, skip_schema_validation=True)
def 