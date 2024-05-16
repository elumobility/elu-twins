import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from ocpp.v16.enums import ChargePointStatus
from sqlmodel import Session, select
from elu.twin.data.enums import ChargingProfileStatusv16, Protocol
from elu.twin.backend.crud.user import get_current_active_user
from elu.twin.backend.db.database import get_session
from elu.twin.backend.routes.v1.common.charge_point_actions import (
    _post_request_start_charging,
    _stop_charging,
)
from ocpp.v16 import call
from elu.twin.charge_point.celery_factory import create_charger, app_celery
from elu.twin.data.enums import (
    ConnectorStatus,
    EvseStatus,
)
from elu.twin.data.schemas.actions import (
    ActionMessageRequest,
    RequestConnectChargePoint,
    RequestDisconnectChargePoint,
)
from elu.twin.data.schemas.transaction import (
    OutputTransaction,
    RequestStartTransaction,
    RequestStopTransaction,
)
from elu.twin.data.tables import (
    User,
    ChargePoint,
)

router = APIRouter(
    prefix="/twin/charge-point/action",
    tags=["Charge point"],
)


@router.post("/start-transaction", response_model=OutputTransaction)
def post_request_start_charging(
    *,
    session: Session = Depends(get_session),
    start_transaction: RequestStartTransaction,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return _post_request_start_charging(session, start_transaction, current_user)


@router.post("/stop-transaction", response_model=ActionMessageRequest)
def stop_charging(
    *,
    session: Session = Depends(get_session),
    stop_transaction: RequestStopTransaction,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return _stop_charging(session, stop_transaction, current_user)


@router.post("/connect-charger", response_model=ActionMessageRequest)
def connect_charger(
    *,
    session: Session = Depends(get_session),
    connect_charge_point: RequestConnectChargePoint,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    charge_point = session.exec(
        select(ChargePoint)
        .where(ChargePoint.id == connect_charge_point.charge_point_id)
        .where(ChargePoint.user_id == current_user.id)
    ).first()
    if charge_point.ocpp_protocol == Protocol.v201:
        charge_point.boot_reason = connect_charge_point.boot_reason
    if charge_point:
        if charge_point.csms_url is None:
            raise HTTPException(
                status_code=400,
                detail="CSMS is not defined for this charge point, please define a valid CSMS url first",
            )
        if charge_point.status == ChargePointStatus.unavailable:
            charge_point.status = ChargePointStatus.preparing
            evses = charge_point.evses
            for evse in evses:
                evse.status = EvseStatus.pending
                connectors = evse.connectors
                for connector in connectors:
                    connector.status = ConnectorStatus.pending
            charge_point_task_id = create_charger.delay(
                json.dumps({"charge_point_id": charge_point.id})
            )
            charge_point.charge_point_task_id = str(charge_point_task_id)
            session.commit()
            return ActionMessageRequest(message="Connect charge point requested")
        raise HTTPException(status_code=400, detail="Charge point not out of service")
    raise HTTPException(status_code=400, detail="Charge point not found")


@router.post("/disconnect-charger")
def disconnect_charger(
    *,
    session: Session = Depends(get_session),
    disconnect_charge_point: RequestDisconnectChargePoint,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    charge_point = session.exec(
        select(ChargePoint)
        .where(ChargePoint.id == disconnect_charge_point.charge_point_id)
        .where(ChargePoint.user_id == current_user.id)
    ).first()
    if charge_point:
        if charge_point.status not in [ChargePointStatus.unavailable]:
            if charge_point.charge_point_task_id:
                charge_point.status = ChargePointStatus.unavailable
                evses = charge_point.evses
                for evse in evses:
                    evse.status = EvseStatus.unavailable
                    connectors = evse.connectors
                    for connector in connectors:
                        connector.status = ConnectorStatus.unavailable
                    # Disconnect the charger
                    # Kill task
                app_celery.control.revoke(
                    charge_point.charge_point_task_id, terminate=True, signal="SIGKILL"
                )
                session.commit()
                return ActionMessageRequest(message="Disconnect charge point requested")
            raise HTTPException(status_code=400, detail="Charge point not connected")
    raise HTTPException(status_code=400, detail="Charge point not found")


@router.post("/charging-profile", response_model=ChargingProfileStatusv16)
def set_charging_profile(
    *,
    session: Session = Depends(get_session),
    charge_profile_request: call.SetChargingProfilePayload,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return _set_charging_profile(session, charge_profile_request, current_user)
