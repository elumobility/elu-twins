from __future__ import annotations
from datetime import datetime, timedelta

from ocpp.v16.datatypes import ChargingProfile, ChargingSchedule, ChargingSchedulePeriod
from ocpp.v16.enums import ChargingRateUnitType
from sqlmodel import Field, SQLModel


class Interval(SQLModel):
    start_time: datetime
    end_time: datetime
    value: float
    stack_level: int

    def contains_overlap(self, other: Interval) -> bool:
        return not (
            (self.start_time >= other.end_time) or (self.end_time <= other.start_time)
        )

    def merge_interval(self, other: Interval) -> list[Interval]:
        first = Interval(
            start_time=self.start_time,
            end_time=self.end_time,
            value=self.value,
            stack_level=self.stack_level,
        )
        second = other
        if first.start_time > second.start_time:
            first, second = second, first
        if first.end_time <= second.start_time:
            return [first, second]
        if first.end_time < second.end_time:
            if first.stack_level > second.stack_level:
                second.start_time = first.end_time
                return [first, second]
            else:
                first.end_time = second.start_time
                return [first, second]
        elif first.end_time == second.end_time:
            if first.stack_level > second.stack_level:
                return [first]
            else:
                first.end_time = second.start_time
                return [first, second]
        else:
            if first.stack_level > second.stack_level:
                return [first]
            else:
                third = Interval(
                    start_time=second.end_time,
                    end_time=first.end_time,
                    value=first.value,
                    stack_level=first.stack_level,
                )
                first.end_time = second.start_time
                return [first, second, third]


class Schedule(SQLModel):
    intervals: list[Interval] = Field(default_factory=list)

    def insert_interval(self, interval: Interval):
        if len(self.intervals) == 0:
            self.intervals.append(interval)
            return None
        else:
            if interval.end_time <= self.intervals[0].start_time:
                self.intervals = [interval] + self.intervals
                return None
            elif interval.start_time >= self.intervals[-1].end_time:
                self.intervals.append(interval)
                return None
            else:
                for i in range(len(self.intervals) - 1):
                    if (
                        self.intervals[i].end_time >= interval.start_time
                        and self.intervals[i + 1].start_time >= interval.end_time
                    ):
                        self.intervals = (
                            self.intervals[: (i + 1)]
                            + [interval]
                            + self.intervals[(i + 1) :]
                        )
                        return None

    def add_interval(self, new_interval: Interval):
        _new_interval = new_interval
        while True:
            interval_overlapping = next(
                (
                    (i, interval)
                    for i, interval in enumerate(self.intervals)
                    if interval.contains_overlap(_new_interval)
                ),
                None,
            )
            if interval_overlapping:
                index, interval = interval_overlapping
                end = interval.end_time
                new_intervals: list[Interval] = interval.merge_interval(_new_interval)
                del self.intervals[index]
                stop = True
                for new_int in new_intervals:
                    if new_int.end_time <= end:
                        self.insert_interval(new_int)
                    else:
                        stop = False
                        _new_interval = new_int
                if stop:
                    break
            else:
                self.insert_interval(_new_interval)
                break

    def add_intervals(self, intervals: list[Interval]):
        for interval in intervals:
            self.add_interval(interval)

    def to_periods(self) -> list[ChargingSchedulePeriod]:
        periods = []
        for interval in self.intervals:
            period = ChargingSchedulePeriod(
                start_period=int(
                    (interval.start_time - self.intervals[0].start_time).total_seconds()
                ),
                limit=interval.value,
            )
            periods.append(period)
        return periods

    def from_ocpp_charging_profiles(
        self,
        profiles: list[ChargingProfile],
        duration: int,
        charging_rate_unit: ChargingRateUnitType,
    ) -> ChargingSchedule:
        now = datetime.utcnow()
        end_schedule = now + timedelta(seconds=duration)
        all_intervals = []
        min_charging_rate = 0
        for profile in profiles:
            stack_level = profile.stack_level
            start = datetime.strptime(
                profile.charging_schedule.start_schedule, "%Y-%m-%dT%H:%M:%S.%f"
            )
            min_charging_rate = max(
                min_charging_rate, profile.charging_schedule.min_charging_rate
            )
            n_intervals = len(profile.charging_schedule.charging_schedule_period)
            for i in range(n_intervals):
                period = profile.charging_schedule.charging_schedule_period[i]
                if i + 1 < n_intervals:
                    _duration = profile.charging_schedule.charging_schedule_period[
                        i + 1
                    ].start_period
                else:
                    _duration = duration
                _interval = Interval(
                    start_time=start + timedelta(seconds=period.start_period),
                    end_time=start + timedelta(seconds=_duration),
                    value=period.limit,
                    stack_level=stack_level,
                )
                all_intervals.append(_interval)
        _intervals = []
        for _interval in all_intervals:
            if _interval.end_time <= end_schedule:
                _intervals.append(_interval)
            else:
                _interval.end_time = end_schedule
                _intervals.append(_interval)
                break

        self.add_intervals(_intervals)
        new_periods = self.to_periods()

        charging_schedule = ChargingSchedule(
            duration=int(
                (_intervals[-1].end_time - _intervals[0].start_time).total_seconds()
            ),
            start_schedule=_intervals[0].start_time.isoformat(),
            charging_rate_unit=charging_rate_unit,
            charging_schedule_period=new_periods,
            min_charging_rate=min_charging_rate,
        )

        return charging_schedule
