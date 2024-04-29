from typing import List

from elu.twin.data.schemas.user import OutputUser, InputUser
from elu.twin.data.tables import User, Quota
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from elu.twin.backend.crud.user import try_to_add_user
from elu.twin.backend.db.database import get_session

router = APIRouter(
    prefix="/user",
    tags=["User"],
)


@router.get("/", response_model=List[OutputUser])
async def get_users(*, session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users


@router.post("/", response_model=OutputUser)
def create_user(*, session: Session = Depends(get_session), user: InputUser):
    db_user = try_to_add_user(user)
    if not db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    if user.quota_id:
        db_user.quota_id = user.quota_id
    else:
        quota = Quota()
        session.add(quota)
        session.commit()
        db_user.quota_id = quota.id
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
