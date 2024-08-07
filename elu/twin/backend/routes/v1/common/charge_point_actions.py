from pydantic import parse_obj_as
import redis
from elu.twin.data.enums import (
    VehicleStatus,
    EvseStatus,
    ConnectorStatus,
    TransactionStatus,
)
from elu.twin.data.schemas.actions import ActionMessageRequest
from elu.twin.data.schemas.charging_profile import (
    AssignedChargingProfile,
    ChargingProfile,
    ChargingSchedule,
    ChargingSchedulePeriod,
    SetChargingProfilePayload,
)
from elu.twin.data.schemas.transaction import (
    RequestStartTransaction,
    RedisRequestStartTransaction,
    RequestStopTransaction,
    RedisRequestStopTransaction,
)
from ocpp.v16 import call
from dataclasses import asdict

from elu.twin.data.tables import User, Connector, Vehicle, Transaction
from fastapi import HTTPException, status
from sqlmodel import Session, select

from elu.twin.backend.env import REDIS_HOSTNAME, REDIS_PORT, REDIS_DB_ACTIONS


def _post_request_start_charging(
    session: Session, start_transaction: RequestStartTransaction, current_user: User
):
    connector = session.exec(
        select(Connector).where(Connector.id == start_transaction.connector_id)
    ).first()
    if connector is None:
        raise HTTPException(status_code=400, detail="Connector not found")
    evse = connector.evse
    charger = evse.charge_point
    if charger.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Connector not found")
    if (
        connector.vehicle_id
        and start_transaction.vehicle_id
        and (connector.vehicle_id != start_transaction.vehicle_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connector already in use by another vehicle",
        )
    if start_transaction.vehicle_id:
        vehicle = session.exec(
            select(Vehicle)
            .where(Vehicle.id == start_transaction.vehicle_id)
            .where(Vehicle.user_id == current_user.id)
        ).first()
    elif connector.vehicle_id:
        vehicle = session.exec(
            select(Vehicle)
            .where(Vehicle.id == connector.vehicle_id)
            .where(Vehicle.user_id == current_user.id)
        ).first()
    else:
        raise HTTPException(
            status_code=400,
            detail="Vehicle not specified and not vehicle connected to connector",
        )
    if not vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    elif vehicle.status != VehicleStatus.ready_to_charge:
        raise HTTPException(status_code=400, detail="Vehicle not ready to charge")
    if (connector.status == ConnectorStatus.available) and (
        connector.evse.status == EvseStatus.available
    ):
        transaction = Transaction(
            charge_point_id=charger.id,
            evse_id=evse.id,
            connector_id=start_transaction.connector_id,
            vehicle_id=vehicle.id,
            user_id=current_user.id,
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        r = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT, db=REDIS_DB_ACTIONS)
        redis_start_transaction = RedisRequestStartTransaction(
            transaction_id=transaction.id
        )
        r.publish(
            f"actions-{charger.id}",
            redis_start_transaction.model_dump_json(),
        )
        connector.status = ConnectorStatus.pending
        connector.vehicle_id = start_transaction.vehicle_id
        vehicle.status = VehicleStatus.pending
        connector.transaction_id = transaction.id
        vehicle.transaction_id = transaction.id
        session.add(connector)
        session.add(vehicle)
        session.commit()
        return transaction
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Connector not available: evse {connector.evse.status}, connector {connector.status}",
    )


def _stop_charging(
    session: Session,
    stop_transaction: RequestStopTransaction,
    current_user: User,
):
    transaction = session.exec(
        select(Transaction)
        .where(Transaction.id == stop_transaction.transaction_id)
        .where(Transaction.user_id == current_user.id)
    ).first()
    if transaction:
        if transaction.status in [
            TransactionStatus.accepted,
            TransactionStatus.running,
        ]:
            r = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT, db=REDIS_DB_ACTIONS)
            redis_stop_transaction = RedisRequestStopTransaction(
                transaction_id=transaction.id
            )
            r.publish(
                f"actions-{transaction.charge_point_id}",
                redis_stop_transaction.model_dump_json(),
            )
            return ActionMessageRequest(
                message="Stop transaction sent to requested connector"
            )
        raise HTTPException(status_code=400, detail="Connector not charging")
    raise HTTPException(status_code=400, detail="Transaction not found")


def convert_assigned_to_charging_profile(
    assigned_profile: AssignedChargingProfile,
) -> ChargingProfile:
    # Convert ChargingSchedulePeriod SQLModel instances to dataclass instances
    charging_schedule_periods = [
        ChargingSchedulePeriod(
            id=period.id,
            start_period=period.start_period,
            limit=period.limit,
            number_phases=period.number_phases,
        )
        for period in assigned_profile.charging_schedule_period
    ]

    # Create the ChargingSchedule dataclass instance
    charging_schedule = ChargingSchedule(
        charging_rate_unit=assigned_profile.charging_rate_unit,
        charging_schedule_period=charging_schedule_periods,
        duration=assigned_profile.duration,
        start_schedule=assigned_profile.start_schedule,
        min_charging_rate=assigned_profile.min_charging_rate,
    )

    # Create the ChargingProfile dataclass instance
    charging_profile = ChargingProfile(
        charging_profile_id=assigned_profile.chargingprofileid,
        stack_level=assigned_profile.stack_level,
        charging_profile_purpose=assigned_profile.charging_profile_purpose,
        charging_profile_kind=assigned_profile.charging_profile_kind,
        charging_schedule=charging_schedule,
        transaction_id=assigned_profile.transaction_id,
        recurrency_kind=assigned_profile.recurrency_kind,
        valid_from=assigned_profile.valid_from,
        valid_to=assigned_profile.valid_to,
    )

    return charging_profile


def _set_charging_profile(
    session: Session, charge_profile_request: AssignedChargingProfile, charge_point_id
):
    charging_profile = convert_assigned_to_charging_profile(
        assigned_profile=charge_profile_request
    )

    profile1 = SetChargingProfilePayload(
        connector_id=1, cs_charging_profiles=charging_profile
    )
    # return profile1

    r = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT, db=REDIS_DB_ACTIONS)
    r.publish(
        f"actions-{charge_point_id}",
        profile1.model_dump_json(),
    )
    return ActionMessageRequest(message="Charging profile sent to requested charger")
    #     raise HTTPException(status_code=400, detail="Connector not charging")
    # raise HTTPException(status_code=400, detail="Transaction not found")
