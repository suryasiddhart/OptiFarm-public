"""Soil-moisture signal generators for simulated devices.

Each step the soil dries a little (faster around midday, following a
daylight curve), occasionally an irrigation event pushes moisture back up,
and a small amount of sensor noise is added. Values stay within
[min_value, max_value]. Each device gets its own seeded RNG, so devices
differ but a given seed always reproduces the same series.
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime

from grid import cell_key


@dataclass
class MoistureProfile:
    start: float = 35.0
    min_value: float = 8.0
    max_value: float = 45.0
    # % moisture lost per hour at the hottest time of day; ~25% of it at night
    dry_rate_per_hour: float = 0.8
    # Irrigation starts when moisture falls below this level...
    irrigation_threshold: float = 18.0
    # ...or at random, with this probability per hour
    random_irrigation_per_hour: float = 0.02
    irrigation_boost: tuple[float, float] = (12.0, 22.0)
    noise: float = 0.3


class MoistureGenerator:
    def __init__(self, profile: MoistureProfile, seed: int | str):
        self.profile = profile
        self.rng = random.Random(seed)
        self.level = min(max(profile.start, profile.min_value), profile.max_value)

    @staticmethod
    def _daylight_factor(at: datetime) -> float:
        """0.25 at night up to 1.0 at 13:00 local-ish (UTC hour used as a proxy)."""
        hour = at.hour + at.minute / 60
        sun = math.cos((hour - 13) / 24 * 2 * math.pi)
        return 0.25 + 0.75 * max(sun, 0.0)

    def next(self, at: datetime, elapsed_seconds: float) -> float:
        p = self.profile
        hours = elapsed_seconds / 3600
        self.level -= p.dry_rate_per_hour * self._daylight_factor(at) * hours

        irrigate = self.level < p.irrigation_threshold or \
            self.rng.random() < p.random_irrigation_per_hour * hours
        if irrigate:
            self.level += self.rng.uniform(*p.irrigation_boost)

        self.level = min(max(self.level, p.min_value), p.max_value)
        reading = self.level + self.rng.gauss(0, p.noise)
        return round(min(max(reading, p.min_value), p.max_value), 2)


class FieldMoistureGenerator:
    """Moisture for every cell of a rows x cols field grid.

    The field follows one MoistureGenerator curve (drying, irrigation); each
    cell adds its own fixed offset (soil and drainage differ across a field)
    plus per-reading sensor noise. Cells are keyed m<row>_<col> (1-based).
    """

    def __init__(self, profile: MoistureProfile, seed: int | str, rows: int, cols: int,
                 cell_spread: float = 3.0):
        self.profile = profile
        self.field = MoistureGenerator(profile, seed)
        rng = random.Random(f"{seed}-cells")
        self.offsets = {cell_key(r, c): rng.gauss(0, cell_spread)
                        for r in range(1, rows + 1) for c in range(1, cols + 1)}
        self.rng = random.Random(f"{seed}-noise")

    def next(self, at: datetime, elapsed_seconds: float) -> dict[str, float]:
        base = self.field.next(at, elapsed_seconds)
        p = self.profile
        return {key: round(min(max(base + offset + self.rng.gauss(0, p.noise), p.min_value),
                               p.max_value), 2)
                for key, offset in self.offsets.items()}

