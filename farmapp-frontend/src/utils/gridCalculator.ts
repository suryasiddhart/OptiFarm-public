import type { SensorGrid, GridCell, MoistureReading } from "../types";

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
  const rows = Math.max(1, Math.floor(fieldLength / cropInterval));
  const cols = Math.max(1, Math.floor(fieldBreadth / cropInterval));

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
 * Maps moisture readings to the nearest grid cells.
 * Assigns readings to cells based on deviceid hash or round-robin.
 * @param grid - The empty sensor grid
 * @param readings - Moisture readings from the API
 * @returns Updated grid with moisture data filled in
 */
export function mapReadingsToGrid(
  grid: SensorGrid,
  readings: MoistureReading[]
): SensorGrid {
  if (readings.length === 0) return grid;

  const totalCells = grid.rows * grid.cols;
  const newCells = grid.cells.map((row) =>
    row.map((cell) => ({ ...cell }))
  );

  // Distribute readings across grid cells
  readings.forEach((reading, index) => {
    const cellIndex = index % totalCells;
    const row = Math.floor(cellIndex / grid.cols);
    const col = cellIndex % grid.cols;

    if (row < grid.rows && col < grid.cols) {
      newCells[row][col] = {
        row,
        col,
        moisture: reading.moisture,
        deviceid: reading.deviceid,
        timestamp: reading.rtctime,
      };
    }
  });

  return { ...grid, cells: newCells };
}
