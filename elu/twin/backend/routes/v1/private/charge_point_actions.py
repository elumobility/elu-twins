from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from elu.twin.backend.db.database import get_session
from elu.twin.backend.routes.v1.common.charge_point_actions import (
    _post_request_start_charging,
    _stop_charging,
)
from elu.twin.data.schemas.actions import (
    ActionMessageRequest,
)
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.transaction import (
    OutputTransaction,
    RequestStartTransaction,
    RequestStopTransaction,
)
from elu.twin.data.tables import (
    User,
)

router = APIRouter(
    prefix="/twin/charge-point/action",
    tags=["Charge point"],
)


@router.post("/start-transaction/{user_id}", response_model=OutputTransaction)
def post_request_start_charging(
    *,
    session: Session = Depends(get_session),
    user_id: Index,
    start_transaction: RequestStartTransaction,
):
    current_user = session.exec(select(User).where(User.id == user_id)).first()
    if not current_user:
        raise HTTPException(status_code=400, detail="User not found")
    return _post_request_start_charging(session, start_transaction, current_user)


@router.post("/stop-transaction/{user_id}", response_model=ActionMessageRequest)
def stop_charging(
    *,
    session: Session = Depends(get_session),
    stop_transaction: RequestStopTransaction,
    user_id: Index,
):
    current_user = session.exec(select(User).where(User.id == user_id)).first()
    if not current_user:
        raise HTTPException(status_code=400, detail="User not found")
    return _stop_charging(session, stop_transaction, current_user)
