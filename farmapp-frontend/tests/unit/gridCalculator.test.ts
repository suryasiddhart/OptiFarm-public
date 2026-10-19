import { describe, it, expect } from "vitest";
import { calculateGrid, mapReadingsToGrid, parseCellKey } from "../../src/utils/gridCalculator";
import type { MoistureReading } from "../../src/types";

const FLOAT4_TENTH = 0.10000000149011612; // 0.1 as stored in a float4 column

const reading = (rtctime: string, moisture: Record<string, number> | null, deviceid = "dev-001"): MoistureReading => ({
  moisture, rtctime, deviceid, userinfo: 100001, fieldid: 200001,
});

describe("calculateGrid", () => {
  it.each([
    [2, 2, 0.1, 20, 20],
    [2, 2, FLOAT4_TENTH, 20, 20], // 19 x 19 without the tolerance
    [0.3, 0.3, 0.1, 3, 3],
    [10, 4, 2, 5, 2],
    [0.05, 0.05, 0.1, 1, 1],
  ])("%s x %s at interval %s → %i x %i", (length, breadth, interval, rows, cols) => {
    const grid = calculateGrid(length, breadth, interval);
    expect([grid.rows, grid.cols]).toEqual([rows, cols]);
    expect(grid.cells.length).toBe(rows);
    expect(grid.cells[0].length).toBe(cols);
  });
});

describe("parseCellKey", () => {
  it("parses 1-based keys to zero-based positions", () => {
    expect(parseCellKey("m1_1")).toEqual({ row: 0, col: 0 });
    expect(parseCellKey("m12_3")).toEqual({ row: 11, col: 2 });
  });

  it.each(["m11", "m0_1", "m1_0", "x1_1", "m1_1_1"])("rejects %s", (key) => {
    expect(parseCellKey(key)).toBeNull();
  });
});

describe("mapReadingsToGrid", () => {
  const grid = () => calculateGrid(2, 2, 1); // 2 x 2

  it("places each cell value by its key", () => {
    const result = mapReadingsToGrid(grid(), [
      reading("2026-10-16T10:00:00Z", { m1_1: 31.4, m1_2: 32.34, m2_1: 12.33, m2_2: 56.78 }),
    ]);
    expect(result.cells.map((row) => row.map((c) => c.moisture))).toEqual([[31.4, 32.34], [12.33, 56.78]]);
    expect(result.cells[1][0].deviceid).toBe("dev-001");
  });

  it("keeps the newest value per cell and fills gaps from older readings", () => {
    const result = mapReadingsToGrid(grid(), [
      reading("2026-10-16T09:00:00Z", { m1_1: 10, m2_2: 20 }),
      reading("2026-10-16T10:00:00Z", { m1_1: 30 }),
    ]);
    expect(result.cells[0][0]).toMatchObject({ moisture: 30, timestamp: "2026-10-16T10:00:00Z" });
    expect(result.cells[1][1]).toMatchObject({ moisture: 20, timestamp: "2026-10-16T09:00:00Z" });
    expect(result.cells[0][1].moisture).toBeNull();
  });

  it("ignores cells outside the grid, malformed keys and legacy readings", () => {
    const result = mapReadingsToGrid(grid(), [
      reading("2026-10-16T10:00:00Z", { m3_1: 1, m11: 2, m1_1: 5 }),
      reading("2026-10-16T08:00:00Z", null),
    ]);
    expect(result.cells.flat().filter((c) => c.moisture !== null)).toHaveLength(1);
  });
});
