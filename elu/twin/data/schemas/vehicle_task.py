from datetime import datetime

from sqlmodel import SQLModel, Field

from elu.twin.data.enums import TaskType, TaskStatus
from elu.twin.data.schemas.location import Location, GPSLocation
from elu.twin.data.schemas.state import State


class VehicleTask(SQLModel):
    task_id: str = Field(...)
    task_type: TaskType = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    initial_location: Location = Field(...)
    end_location: Location = Field(...)
    initial_odometer: float | None = Field(None)
    final_odometer: float | None = Field(None)
    initial_soc: float | None = Field(None)
    final_soc: float | None = Field(None)
    distance: float | None = Field(None)
    status: TaskStatus = Field(TaskStatus.scheduled)

    def get_status_at(
        self,
        time: datetime,
        battery: float | None = None,
        charging_rate: float | None = None,
        energy_consumption: float | None = None,
    ) -> State | None:
        self.end_time = self.end_time.replace(tzinfo=None)
        self.start_time = self.start_time.replace(tzinfo=None)

        if time > self.end_time or time < self.start_time:
            return None
        duration = (self.end_time - self.start_time).total_seconds() / 3600.0
        time_point = (time - self.start_time).total_seconds() / 3600.0
        fraction = time_point / duration
        state = State(
            location=self.initial_location,
            speed=0,
            odometer=self.initial_odometer,
            energy_source_level=self.initial_soc,
            timestamp=time,
        )
        if self.task_type == TaskType.traveling:
            state.speed = (self.final_odometer - self.initial_odometer) / duration
            distance = state.speed * time_point
            state.odometer += distance
            consumption_kwh = int(state.odometer * energy_consumption)
            consumption_soc = int((consumption_kwh / battery) * 100)
            state.energy_source_level -= consumption_soc
            state.location = Location(
                gps_location=GPSLocation(
                    latitude=self.initial_location.gps_location.latitude
                    + (
                        self.initial_location.gps_location.latitude
                        - self.initial_location.gps_location.latitude
                    )
                    * fraction,
                    longitude=self.initial_location.gps_location.longitude
                    + (
                        self.initial_location.gps_location.longitude
                        - self.initial_location.gps_location.longitude
                    )
                    * fraction,
                )
            )
        elif self.task_type == TaskType.charging:
            soc_variation = charging_rate * time_point
            energy_source_level = min(
                100, int(state.energy_source_level + soc_variation)
            )
            state.energy_source_level = energy_source_level
        return state
