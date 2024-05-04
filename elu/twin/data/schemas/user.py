import re
from typing import Optional

from pydantic import field_validator, EmailStr
from sqlmodel import Field, SQLModel

from elu.twin.data.schemas.common import TimestampBase, Index
from elu.twin.data.schemas.quota import OutputQuota


class BaseUser(SQLModel):
    username: str = Field(
        index=True, unique=True, description="username", alias="email"
    )

    @field_validator("username")
    @classmethod
    def check_email(cls, value) -> str:
        # use a regex to check that the email has a valid format
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("Invalid email address, username must be an email address")
        return value


class InputUser(BaseUser):
    password: str
    quota_id: Optional[int] = Field(None)

    @field_validator("password")
    @classmethod
    def check_password(cls, value) -> str:
        # convert the password to a string if it is not already
        value = str(value)
        # check that the password has at least 8 characters, one uppercase letter, one lowercase letter, and one digit
        if len(value) < 8:
            raise ValueError("Password must have at least 8 characters")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must have at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must have at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must have at least one digit")
        return value


class OutputUser(BaseUser, TimestampBase):
    id: Index
    quota: OutputQuota


class UpdateUser(SQLModel):
    username: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    max_number_of_charge_points: int | None = None
    max_number_of_charge_point_connectors: int | None = None
    max_number_of_vehicles: int | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value) -> str:
        # convert the password to a string if it is not already
        if value is None:
            return None
        value = str(value)
        # check that the password has at least 8 characters, one uppercase letter, one lowercase letter, and one digit
        if len(value) < 8:
            raise ValueError("Password must have at least 8 characters")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must have at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must have at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must have at least one digit")
        return value
