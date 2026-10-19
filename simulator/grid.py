"""Field moisture grid: size and cell keys.

A field is divided into rows = floor(fieldlength / cropinterval) and
cols = floor(fieldbreadth / cropinterval) cells. Moisture readings are stored
as {"m<row>_<col>": value} with 1-based row/col, e.g. {"m1_1": 31.4, "m1_2": 32.3}.

Keep in step with api/utils/grid.py, ingest/grid.py and
farmapp-frontend/src/utils/gridCalculator.ts.
"""

import math
import re

CELL_KEY_PATTERN = r"^m([1-9][0-9]*)_([1-9][0-9]*)$"
_CELL_KEY = re.compile(CELL_KEY_PATTERN)

# Field sizes are stored as float4: 0.1 comes back as 0.10000000149, and
# 2 / 0.10000000149 = 19.9999997 would round down to 19 instead of 20.
_EPSILON = 1e-6


def grid_size(length: float, breadth: float, interval: float) -> tuple[int, int]:
    """(rows, cols) of a field; at least 1 x 1."""
    if interval <= 0:
        raise ValueError("crop interval must be positive")
    rows = max(1, math.floor(length / interval + _EPSILON))
    cols = max(1, math.floor(breadth / interval + _EPSILON))
    return rows, cols


def cell_key(row: int, col: int) -> str:
    return f"m{row}_{col}"


def parse_cell_key(key: str) -> tuple[int, int] | None:
    match = _CELL_KEY.match(key)
    return (int(match.group(1)), int(match.group(2))) if match else None


def cells_outside_grid(cells: dict, rows: int, cols: int) -> list[str]:
    """Keys that are malformed or fall outside a rows x cols grid."""
    outside = []
    for key in cells:
        position = parse_cell_key(key)
        if position is None or position[0] > rows or position[1] > cols:
            outside.append(key)
    return outside
