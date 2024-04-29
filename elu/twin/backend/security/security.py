from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from elu.twin.backend.env import SECRET_KEY
from elu.twin.backend.env import ACCESS_TOKEN_EXPIRE_MINUTES
from elu.twin.data.helpers import get_now

# to get a string like this run:
# openssl rand -hex 32
ALGORITHM = "HS256"


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = get_now(as_string=False) + expires_delta
    else:
        expire = get_now(as_string=False) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
