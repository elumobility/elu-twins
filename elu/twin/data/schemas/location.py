from sqlmodel import SQLModel, Field


class GPSLocation(SQLModel):
    latitude: float
    longitude: float
    altitude: float | None = None


class Location(SQLModel):
    name: str = Field(default="unknown")
    gps_location: GPSLocation
