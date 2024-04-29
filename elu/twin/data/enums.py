from enum import StrEnum

from ocpp.v201.enums import ConnectorType


class EvseStatus(StrEnum):
    available = "available"
    charging = "charging"
    occupied = "occupied"
    unavailable = "unavailable"
    out_of_service = "out-of-service"
    pending = "pending"
    busy = "busy"


class ConnectorStatus(StrEnum):
    available = "available"
    charging = "charging"
    occupied = "occupied"
    unavailable = "unavailable"
    out_of_service = "out-of-service"
    pending = "pending"
    preparing = "preparing"
    finishing = "finishing"


class TransactionName(StrEnum):
    start_transaction = "StartTransaction"
    stop_transaction = "StopTransaction"


class TransactionStatus(StrEnum):
    accepted = "Accepted"
    rejected = "Rejected"
    pending = "Pending"
    unknown = "Unknown"
    running = "Charging"
    completed = "Completed"
    aborted = "Aborted"
    faulted = "Faulted"


class VehicleStatus(StrEnum):
    available = "available"
    charging = "charging"
    occupied = "occupied"
    driving = "driving"
    ready_to_charge = "ready-to-charge"
    out_of_service = "out-of-service"
    pending = "pending"


def is_dc(connector_type: ConnectorType):
    """

    :param connector_type:
    :return:
    """
    dc_type = [ConnectorType.c_ccs1, ConnectorType.c_ccs2]
    return connector_type in dc_type


class PowerType(StrEnum):
    """Power types"""

    ac = "AC"
    dc = "DC"


class AuthMethod(StrEnum):
    """Authentication methods"""

    cache = "cache"
    list = "list"


class SharePowerPolicy(StrEnum):
    equal = "Equal"


class ConnectorQueuedActions(StrEnum):
    stop_charging = "stop-charging"


class Protocol(StrEnum):
    """Define charge_point protocols"""

    v16 = "ocpp1.6"
    v201 = "ocpp2.0.1"


class TaskType(StrEnum):
    loading = "loading"
    unloading = "unloading"
    charging_window = "charging-window"
    charging = "charging"
    traveling = "traveling"
    waiting = "waiting"


class TaskStatus(StrEnum):
    scheduled = "scheduled"
    in_progress = "in-progress"
    finished = "finished"
    cancelled = "cancelled"


class EnergySource(StrEnum):
    ev = "ev"
    gas = "gas"
    diesel = "diesel"
    hybrid = "hybrid"
