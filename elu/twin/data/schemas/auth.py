from datetime import datetime

from ocpp.v16.enums import AuthorizationStatus
from sqlmodel import Field

from elu.twin.data.enums import AuthMethod
from elu.twin.data.schemas.common import TableBase, Index


class BaseAuthV16(TableBase):
    """BaseAuthV16"""

    id_tag: str = Field(description="Identifier tag", index=True)
    auth_method: AuthMethod = Field(description="Authentication method")
    status: AuthorizationStatus | None = Field(
        default=None, description="Authorization status"
    )
    parent_id_tag: str | None = Field(default=None, description="Parent identifier tag")
    expiry_date: datetime | None = Field(default=None, description="Expiry date")


class InputAuthV16(BaseAuthV16):
    """InputAuthV16"""

    pass


class OutputAuthV16(BaseAuthV16):
    """OutputAuthV16"""

    charge_point_id: Index | None = Field(description="Charge point id")
