from fastapi import APIRouter, Depends
from elu.twin.data.schemas.quota import OutputQuota
from elu.twin.data.tables import Quota
from elu.twin.backend.db.database import get_session
from elu.twin.data.schemas.common import Index
from sqlmodel import Session, select

router = APIRouter(
    prefix="/twin/quota",
    tags=["Quota"],
)


@router.patch("/{quota_id}/{consumed}", response_model=OutputQuota)
def update_quota(
    *,
    session: Session = Depends(get_session),
    quota_id: Index,
    consumed: float,
):
    """
    Update quota consumed
    :param session:
    :param quota_id:
    :param consumed:
    :return:
    """
    db_quota = session.exec(select(Quota).where(Quota.id == quota_id)).first()
    if not db_quota:
        return {"message": "Quota not found"}
    db_quota.available_tokens -= consumed
    session.add(db_quota)
    session.commit()
    session.refresh(db_quota)
    return db_quota
