"""Device telemetry payload (the MQTT contract) and its conversion to rows.

    {"ts": "2026-10-12T10:00:00Z", "readings": {"moisture": {"m1_1": 31.4, "m1_2": 32.3}}}
    {"batch": [{"ts": "...", "readings": {"moisture": {"m1_1": 31.4}}}, ...]}

`moisture` holds one value per cell of the device's field grid, keyed
m<row>_<col> (1-based, see grid.py). Any subset of cells may be sent; cells
sent again for the same device and `ts` are merged into the stored reading,
so a large grid can be split over several messages with the same `ts`.

`ts` is optional for a single reading: devices without a clock leave it out
and the time the bridge received the message is used. Batched readings must
each carry `ts`, otherwise they would all collide on the same time.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import (BaseModel, ConfigDict, Field, StringConstraints, field_validator,
                      model_validator)

from grid import CELL_KEY_PATTERN

CellKey = Annotated[str, StringConstraints(pattern=CELL_KEY_PATTERN)]


class Readings(BaseModel):
    model_config = ConfigDict(extra="allow")  # other sensors are ignored for now

    moisture: dict[CellKey, float] = Field(min_length=1)

    @field_validator("moisture")
    @classmethod
    def finite(cls, cells: dict[str, float]) -> dict[str, float]:
        bad = [key for key, value in cells.items() if not math.isfinite(value)]
        if bad:
            raise ValueError(f"moisture must be finite numbers: {', '.join(bad[:10])}")
        return cells


class Reading(BaseModel):
    ts: datetime | None = None
    readings: Readings

    @field_validator("ts")
    @classmethod
    def timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("ts must include a timezone (e.g. 2026-10-12T10:00:00Z)")
        return value


class Telemetry(BaseModel):
    ts: datetime | None = None
    readings: Readings | None = None
    batch: list[Reading] | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def one_shape(self) -> "Telemetry":
        if (self.readings is None) == (self.batch is None):
            raise ValueError("send either 'readings' or 'batch'")
        if self.batch is not None and any(r.ts is None for r in self.batch):
            raise ValueError("every reading in 'batch' needs 'ts'")
        if self.ts is not None and self.ts.tzinfo is None:
            raise ValueError("ts must include a timezone (e.g. 2026-10-12T10:00:00Z)")
        return self


@dataclass(frozen=True)
class Row:
    deviceid: str
    rtctime: datetime
    moisture: dict[str, float]


def to_rows(deviceid: str, telemetry: Telemetry, received_at: datetime,
            max_age: timedelta, max_future_skew: timedelta) -> list[Row]:
    """Flatten a payload into rows; raises ValueError for implausible timestamps."""
    items = telemetry.batch or [Reading(ts=telemetry.ts, readings=telemetry.readings)]
    rows = []
    for item in items:
        rtctime = (item.ts or received_at).astimezone(timezone.utc)
        if rtctime < received_at - max_age or rtctime > received_at + max_future_skew:
            raise ValueError(f"ts {rtctime.isoformat()} is outside the accepted window")
        rows.append(Row(deviceid=deviceid, rtctime=rtctime, moisture=item.readings.moisture))
    return rows
