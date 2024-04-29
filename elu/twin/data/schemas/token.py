from sqlmodel import Field, SQLModel

from elu.twin.data.schemas.common import Index, TableBase


class Token(SQLModel):
    access_token: str
    token_type: str


class InputAppToken(SQLModel):
    name: str = Field(description="name of the app")
    expiry_in_days: int = Field(
        ge=1, le=365, description="expiration time of the token in days"
    )


class BaseAppToken(InputAppToken, TableBase):
    token_hint: str = Field(description="token hint")


class OutputFullAppToken(InputAppToken, TableBase):
    token: str = Field(description="token")


class OutputAppToken(InputAppToken, TableBase):
    pass


class TokenData(SQLModel):
    username: str | None = None
    scopes: list[str] = Field(default_factory=list)
