from typing import List

from elu.twin.data.schemas.transaction import OutputTransaction, UpdateTransaction
from elu.twin.data.schemas.common import Index
from fastapi import APIRouter, Depends, HTTPException

from elu.twin.backend.db.database import get_session
from sqlmodel import select, Session
from fastapi import status
from elu.twin.data.tables import Transaction


router = APIRouter(
    prefix="/operations/charge_point/transaction",
    tags=["OCPP transactions"],
)


@router.get("/{transaction_id}", response_model=OutputTransaction)
async def get_transaction(
    *, session: Session = Depends(get_session), transaction_id: Index
):
    """Get transaction by id

    Args:
        session (Session, optional): [description]. Defaults to Depends(get_session).
        transaction_id (Index): [description]
    """
    transaction = session.exec(
        select(Transaction).where(Transaction.id == transaction_id)
    ).first()
    if transaction:
        return transaction
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
    )


# @router.get("/ocpp/{transactionid}", response_model=OutputTransaction)
# async def get_transaction(
#     *, session: Session = Depends(get_session), transactionid: int
# ):
#     """Get transaction by by ocpp transactionid

#     Args:
#         session (Session, optional): [description]. Defaults to Depends(get_session).
#         transaction_id (int): [description]
#     """
#     transaction = session.exec(
#         select(Transaction).where(Transaction.transactionidid == transaction_id)
#     ).first()
#     if transaction:
#         return transaction
#     raise HTTPException(
#         status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
#     )


@router.patch("/{transaction_id}", response_model=OutputTransaction)
async def update_transactions(
    *,
    session: Session = Depends(get_session),
    transaction_id: Index | None,
    update_transaction: UpdateTransaction
):
    transaction = session.exec(
        select(Transaction).where(Transaction.id == transaction_id)
    ).first()
    if transaction:
        for key, value in update_transaction.dict().items():
            if value:
                setattr(transaction, key, value)
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
    )
