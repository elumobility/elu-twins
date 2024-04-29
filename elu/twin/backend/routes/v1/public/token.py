import logging
from datetime import timedelta
from typing import Annotated

from elu.twin.data.schemas.common import Index
from elu.twin.data.tables import User, AppToken
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from sqlmodel import Session, select

from elu.twin.backend.crud.user import authenticate_user, get_current_active_user
from elu.twin.data.schemas.token import (
    Token,
    InputAppToken,
    OutputAppToken,
    OutputFullAppToken,
)

from elu.twin.backend.db.database import get_session
from elu.twin.backend.env import ACCESS_TOKEN_EXPIRE_MINUTES
from elu.twin.backend.security.security import (
    create_access_token,
    get_password_hash,
)

router = APIRouter(prefix="", tags=["Token"], include_in_schema=False)


@router.post("/token", response_model=Token)
@logger.catch
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    print("form_data: ", form_data)
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},  # , "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/app-token", response_model=OutputFullAppToken)
@logger.catch
async def create_app_token(
    *,
    session: Session = Depends(get_session),
    input_token: InputAppToken,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    logging.error(f"input_token: {input_token}")
    access_token_expires = timedelta(minutes=input_token.expiry_in_days * 24 * 60)
    logger.error(f"access_token_expires: {access_token_expires}")
    logger.error(f"current_user: {current_user.username}")
    logger.error(f"current_user: {current_user}")
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "mode": "app",
        },  # , "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )
    logger.error(f"access_token: {access_token}")
    hashed_token = get_password_hash(access_token)
    app_token = AppToken(
        token_hint=access_token[-4:],
        hashed_token=hashed_token,
        user_id=current_user.id,
        expiry_in_days=input_token.expiry_in_days,
        name=input_token.name,
    )
    logger.error(f"AppToken: {app_token}")
    session.add(app_token)
    session.commit()
    session.refresh(app_token)
    result = OutputFullAppToken(
        token=access_token,
        expiry_in_days=input_token.expiry_in_days,
        name=input_token.name,
    )
    print(result)
    return result


@router.get("/app-token/{id}", response_model=OutputAppToken)
@logger.catch
async def get_app_token(
    *,
    session: Session = Depends(get_session),
    id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    token = session.exec(
        select(AppToken)
        .where(AppToken.id == id)
        .where(AppToken.user_id == current_user.id)
    ).first()
    if not token:
        raise HTTPException(status_code=400, detail="Token not found")
    return token


@router.get("/app-token", response_model=list[OutputAppToken])
@logger.catch
async def get_app_tokens(
    *,
    session: Session = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    tokens = session.exec(
        select(AppToken).where(AppToken.user_id == current_user.id)
    ).all()
    return tokens


@router.delete("/app-token/{id}", response_model=OutputAppToken)
@logger.catch
async def delete_app_token(
    *,
    session: Session = Depends(get_session),
    id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    token = session.exec(
        select(AppToken)
        .where(AppToken.id == id)
        .where(AppToken.user_id == current_user.id)
    ).first()
    if not token:
        raise HTTPException(status_code=400, detail="Token not found")
    session.delete(token)
    session.commit()
    return token
