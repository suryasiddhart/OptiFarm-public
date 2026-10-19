import type { SensorGrid, GridCell, MoistureReading } from "../types";

// Field sizes come from float4 columns: 0.1 arrives as 0.10000000149, and
// 2 / 0.10000000149 = 19.9999997 would floor to 19 instead of 20.
// Keep in step with api/utils/grid.py, ingest/grid.py and simulator/grid.py.
const EPSILON = 1e-6;

const CELL_KEY = /^m([1-9][0-9]*)_([1-9][0-9]*)$/;

/** "m<row>_<col>" (1-based) → zero-based { row, col }, or null if malformed. */
export function parseCellKey(key: string): { row: number; col: number } | null {
  const match = CELL_KEY.exec(key);
  return match ? { row: Number(match[1]) - 1, col: Number(match[2]) - 1 } : null;
}

/**
 * Calculates the sensor grid based on field dimensions and crop interval.
 * @param fieldLength - Length of the field in meters
 * @param fieldBreadth - Breadth of the field in meters
 * @param cropInterval - Distance between crops in meters
 * @returns SensorGrid with rows, cols, and empty cells
 */
export function calculateGrid(
  fieldLength: number,
  fieldBreadth: number,
  cropInterval: number
): SensorGrid {
  const rows = Math.max(1, Math.floor(fieldLength / cropInterval + EPSILON));
  const cols = Math.max(1, Math.floor(fieldBreadth / cropInterval + EPSILON));

  const cells: GridCell[][] = [];

  for (let r = 0; r < rows; r++) {
    const row: GridCell[] = [];
    for (let c = 0; c < cols; c++) {
      row.push({
        row: r,
        col: c,
        moisture: null,
        deviceid: null,
        timestamp: null,
      });
    }
    cells.push(row);
  }

  return { rows, cols, cells };
}

/**
 * Fills grid cells from moisture readings ({ m<row>_<col>: value } per reading).
 * Each cell shows its most recent value: readings may cover only part of the
 * grid, so older readings fill the cells newer ones didn't report.
 * @param grid - The empty sensor grid
 * @param readings - Moisture readings from the API (any order)
 * @returns Updated grid with moisture data filled in
 */
export function mapReadingsToGrid(
  grid: SensorGrid,
  readings: MoistureReading[]
): SensorGrid {
  if (readings.length === 0) return grid;

  const newCells = grid.cells.map((row) =>
    row.map((cell) => ({ ...cell }))
  );

  const newestFirst = [...readings].sort(
    (a, b) => Date.parse(b.rtctime) - Date.parse(a.rtctime)
  );
  for (const reading of newestFirst) {
    for (const [key, value] of Object.entries(reading.moisture ?? {})) {
      const position = parseCellKey(key);
      if (!position || position.row >= grid.rows || position.col >= grid.cols) continue;
      const cell = newCells[position.row][position.col];
      if (cell.moisture !== null) continue; // a newer reading already set it
      newCells[position.row][position.col] = {
        ...cell,
        moisture: value,
        deviceid: reading.deviceid,
        timestamp: reading.rtctime,
      };
    }
  }

  return { ...grid, cells: newCells };
}
