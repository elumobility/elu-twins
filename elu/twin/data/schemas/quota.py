from sqlmodel import Field, SQLModel


class QuotaBase(SQLModel):
    max_number_of_charge_points: int = Field(default=20, ge=0)
    max_number_of_vehicles: int = Field(default=20, ge=0)
    current_number_of_charge_points: int = Field(default=0, ge=0)
    current_number_of_vehicles: int = Field(default=0, ge=0)
    available_tokens: int = Field(
        default=1000000, description="Number of tokens available"
    )


class OutputQuota(QuotaBase):
    pass
