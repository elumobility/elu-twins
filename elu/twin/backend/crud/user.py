import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlmodel import Session, select
from starlette import status

from elu.twin.backend.db.database import engine
from elu.twin.backend.env import SECRET_KEY
from elu.twin.data.tables import User, AppToken
from elu.twin.data.schemas.user import InputUser
from elu.twin.data.schemas.token import TokenData
from elu.twin.backend.security.security import (
    oauth2_scheme,
    verify_password,
    ALGORITHM,
    get_password_hash,
)


def get_user_by_username(username: str, app_token: str | None = None) -> User | None:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return None
        if app_token:
            tokens = session.exec(
                select(AppToken).where(AppToken.user_id == user.id)
            ).all()
            is_valid_token = next(
                (
                    True
                    for token in tokens
                    if verify_password(app_token, token.hashed_token)
                ),
                False,
            )
            if not is_valid_token:
                return None
        return user


def try_to_add_user(user: InputUser) -> User | None:
    user_already_exists = get_user_by_username(user.username)
    if user_already_exists:
        return None
    user_in_db = User(
        username=user.username, hashed_password=get_password_hash(user.password)
    )
    return user_in_db


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    # security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)]
):
    authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    app_token = token if "mode" in payload else None
    user = get_user_by_username(username=token_data.username, app_token=app_token)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
