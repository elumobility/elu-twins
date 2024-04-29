from typing import Annotated

from elu.twin.data.schemas.user import OutputUser
from elu.twin.data.tables import User
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from elu.twin.backend.crud.user import get_current_active_user
from elu.twin.backend.db.database import get_session

router = APIRouter(
    prefix="/user",
    tags=["User"],
)


@router.get("/me", response_model=OutputUser)
async def get_users(
    *,
    session: Session = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    user = session.exec(select(User).where(User.id == current_user.id)).first()
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")
