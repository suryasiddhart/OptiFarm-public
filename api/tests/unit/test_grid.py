"""Unit tests for the field grid size and cell keys (utils/grid.py)."""

import pytest

from utils.grid import cell_key, cells_outside_grid, grid_size, parse_cell_key

FLOAT4_TENTH = 0.10000000149011612   # 0.1 as stored in a float4 column


@pytest.mark.unit
class TestGridSize:
    @pytest.mark.parametrize("length, breadth, interval, expected", [
        (2, 2, 0.1, (20, 20)),
        (2, 2, FLOAT4_TENTH, (20, 20)),      # would be 19 x 19 without the tolerance
        (0.3, 0.3, 0.1, (3, 3)),             # 0.3 / 0.1 = 2.9999999999999996
        (10, 4, 2, (5, 2)),
        (1, 1, 0.3, (3, 3)),                 # partial cells are not counted
        (0.05, 0.05, 0.1, (1, 1)),           # never smaller than 1 x 1
    ])
    def test_rows_and_cols(self, length, breadth, interval, expected):
        assert grid_size(length, breadth, interval) == expected

    def test_interval_must_be_positive(self):
        with pytest.raises(ValueError):
            grid_size(2, 2, 0)


@pytest.mark.unit
class TestCellKeys:
    def test_round_trip(self):
        assert cell_key(12, 3) == "m12_3"
        assert parse_cell_key("m12_3") == (12, 3)

    @pytest.mark.parametrize("key", ["m0_1", "m1_0", "m11", "x1_1", "m1_1_1", "m01_1", "M1_1", "m1_"])
    def test_malformed_keys(self, key):
        assert parse_cell_key(key) is None

    def test_cells_outside_grid(self):
        cells = {"m1_1": 1, "m20_20": 2, "m21_1": 3, "m1_21": 4, "bad": 5}
        assert sorted(cells_outside_grid(cells, 20, 20)) == ["bad", "m1_21", "m21_1"]
