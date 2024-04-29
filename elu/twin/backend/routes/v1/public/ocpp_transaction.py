"""OCPP transaction routes"""

from typing import Annotated, List

from elu.twin.data.schemas.transaction import OutputTransaction
from elu.twin.data.schemas.common import Index
from fastapi import APIRouter, Depends, HTTPException

from elu.twin.backend.crud.user import get_current_active_user
from elu.twin.backend.db.database import get_session
from sqlmodel import select, Session
from fastapi import status
from elu.twin.data.tables import User, Transaction

router = APIRouter(
    prefix="/operations/charge_point/transaction",
    tags=["OCPP transactions"],
)


@router.get("/", response_model=List[OutputTransaction])
async def get_transactions(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index | None = None,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get transactions

    Args:
        session (Session, optional): [description]. Defaults to Depends(get_session).
        charge_point_id (Index | None, optional): [description]. Defaults to None.
        current_user (Annotated[User, Depends(get_current_active_user)]): [description]
    """
    query = select(Transaction).where(Transaction.user_id == current_user.id)
    if charge_point_id:
        query = query.where(Transaction.charge_point_id == charge_point_id)
    transactions = session.exec(query).all()
    return transactions


@router.get("/{transaction_id}", response_model=OutputTransaction)
async def get_transaction(
    *,
    session: Session = Depends(get_session),
    transaction_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get transaction by id

    Args:
        session (Session, optional): [description]. Defaults to Depends(get_session).
        transaction_id (Index): [description]
        current_user (Annotated[User, Depends(get_current_active_user)]): [description]
    """
    transaction = session.exec(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .where(Transaction.id == transaction_id)
    ).first()
    if transaction:
        return transaction
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
    )
