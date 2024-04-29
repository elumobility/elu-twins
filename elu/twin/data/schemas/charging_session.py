from __future__ import annotations
from datetime import datetime, timedelta
from typing import Tuple

from sqlmodel import SQLModel, Field

from elu.twin.data.schemas.common import Index
import plotly.express as px
import pandas as pd


class TimeEvent(SQLModel):
    time: datetime = Field(description="Time")
    value: int | float = Field(description="Value")


class TimeSeries(SQLModel):
    data: list[TimeEvent] = Field(default_factory=list, description="Time series data")

    @classmethod
    def from_list(cls, values, time_step: int, start_time: datetime) -> TimeSeries:
        data = [
            TimeEvent(time=start_time + timedelta(seconds=i * time_step), value=value)
            for i, value in enumerate(values)
        ]
        return cls(data=data)

    def to_df(self, value_name: str, id_name: str):
        df = pd.DataFrame(
            [{"time": event.time, value_name: event.value} for event in self.data]
        )
        df["name"] = id_name
        return df

    def to_steps(
        self,
        start_time: datetime,
        end_time: datetime,
        time_step: int,
        null_value: int | None = 0,
    ) -> list[Tuple[int, int]]:
        """

        :param start_time:
        :param end_time:
        :param time_step:
        :param null_value:
        :return:
        """
        timestamps_dict: dict[int, int] = {}
        for event in self.data:
            timestamps_dict[
                int((event.time.timestamp() // time_step) * time_step)
            ] = event.value
        n_start = int(start_time.timestamp() // time_step) - 1
        n_end = int((end_time.timestamp() // time_step)) + 1
        start_timestamp = int(((start_time.timestamp() // time_step) - 1) * time_step)
        result = [
            (i, timestamps_dict.get(start_timestamp + i * time_step, null_value))
            for i in range(n_end - n_start)
        ]
        return result

    @staticmethod
    def get_step_number(time: datetime, start_time: datetime, time_step: int) -> int:
        n_start = int(start_time.timestamp() // time_step) - 1
        return int(time.timestamp() // time_step) - n_start


class ChargingSessionSchedule(SQLModel):
    vehicle_id: Index | None = Field(default=None)
    connector_id: Index | None = Field(default=None)
    start_charging: datetime = Field(description="Arrival time")
    end_charging: datetime = Field(description="Departure time")
    soc_values: TimeSeries = Field(description="State of charge values")
    power_profile: TimeSeries = Field(description="Power profile")
    energy_cost: TimeSeries = Field(description="Cost")
    arrival_time: datetime = Field(description="Arrival time")
    departure_time: datetime = Field(description="Departure time")
    initial_soc: int = Field(ge=0, le=100, description="Initial state of charge")
    target_soc: int = Field(ge=0, le=100, description="Target state of charge")


class ChargingSessionsInCircuit(SQLModel):
    schedules: list[ChargingSessionSchedule] = Field(
        default_factory=list, description="Charging session schedules"
    )
    power_profile: TimeSeries = Field(description="Power profile")
    energy_prices: TimeSeries = Field(description="Cost")

    def to_df(self) -> pd.DataFrame:
        df_power = pd.concat(
            [
                schedule.power_profile.to_df(
                    "power", f"{schedule.vehicle_id} - {schedule.connector_id}"
                )
                for schedule in self.schedules
            ]
        )
        df_soc = pd.concat(
            [
                schedule.soc_values.to_df(
                    "soc", f"{schedule.vehicle_id} - {schedule.connector_id}"
                )
                for schedule in self.schedules
            ]
        )
        df_cost = pd.concat(
            [
                schedule.energy_cost.to_df(
                    "cost", f"{schedule.vehicle_id} - {schedule.connector_id}"
                )
                for schedule in self.schedules
            ]
        )
        df = pd.merge(df_power, df_soc, on=["time", "name"])
        df = pd.merge(df, df_cost, on=["time", "name"])
        return df


class ChargingSessionRequest(SQLModel):
    vehicle_id: Index | None = Field(default=None, foreign_key="vehicle.id")
    initial_soc: int = Field(ge=0, le=100, description="Initial state of charge")
    target_soc: int = Field(ge=0, le=100, description="Target state of charge")
    arrival_time: datetime = Field(description="Arrival time")
    departure_time: datetime = Field(description="Departure time")
    battery_capacity: int = Field(ge=0, description="Battery capacity")
    charge_rate: int = Field(ge=0, description="Charge rate")

    def get_just_charge_price(
        self, charge_point_power: int, prices: TimeSeries, time_step: int
    ):
        power = min(self.charge_rate, charge_point_power)
        steps = int(
            self.battery_capacity
            * (self.target_soc - self.initial_soc)
            * power
            * 3600
            / time_step
        )
        price_steps = prices.to_steps(self.arrival_time, self.departure_time, time_step)
        price = sum(p for _, p in price_steps[:steps])
        return price


class ChargePointAvailability(SQLModel):
    connector_id: Index | None = Field(default=None, foreign_key="connector.id")
    max_power_available: TimeSeries = Field(description="Maximum power available")

    def get_max_power(self):
        return max(d.value for d in self.max_power_available.data)
