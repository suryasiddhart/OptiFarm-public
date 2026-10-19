import { describe, it, expect } from "vitest";
import { countDevicesByField } from "../../src/utils/deviceCounts";
import { cellAtPoint, cellOrigin, heatmapLayout } from "../../src/utils/heatmapLayout";
import { calculateGrid, mapReadingsToGrid } from "../../src/utils/gridCalculator";
import { apiErrorMessage } from "../../src/utils/apiError";
import type { Device } from "../../src/types";

const device = (deviceid: string, fieldid: number | null, status: Device["status"] = "active"): Device => ({
  deviceid, devicename: deviceid, userinfo: 1, fieldid, status, last_seen: null, created_at: "2026-10-18T00:00:00Z",
});

describe("countDevicesByField", () => {
  it("counts active devices per field", () => {
    expect(countDevicesByField([
      device("a", 1), device("b", 1), device("c", 2), device("d", 2, "disabled"), device("e", null),
    ])).toEqual({ 1: 2, 2: 1 });
  });
});

describe("heatmapLayout", () => {
  it("puts m2_5 at the second row and fifth column", () => {
    const grid = mapReadingsToGrid(calculateGrid(2, 2, 0.1), [
      { moisture: { m2_5: 42 }, rtctime: "2026-10-18T10:00:00Z", deviceid: "d", userinfo: 1, fieldid: 1 },
    ]);
    expect(grid.cells[1][4].moisture).toBe(42); // zero-based row 1, col 4

    const layout = heatmapLayout(grid.rows, grid.cols);
    const { x, y } = cellOrigin(layout, 1, 4);
    const half = layout.cellSize / 2;
    expect(cellAtPoint(layout, x + half, y + half)).toEqual({ row: 1, col: 4 });
  });

  it("leaves room for row and column numbers and finds no cell there", () => {
    const layout = heatmapLayout(4, 4);
    expect(layout.originX).toBeGreaterThan(20);
    expect(cellAtPoint(layout, layout.originX - 5, layout.originY + 5)).toBeNull(); // row-number column
    expect(cellAtPoint(layout, layout.originX + 5, layout.originY - 5)).toBeNull(); // column-number row
    expect(cellAtPoint(layout, layout.width - 1, layout.height - 1)).toBeNull();     // right/bottom padding
  });

  it.each([
    [4, 4, 60, true],
    [20, 20, 40, true],
    [100, 40, 24, false],
  ])("%i x %i grid uses %ipx cells", (rows, cols, cellSize, showValues) => {
    const layout = heatmapLayout(rows, cols);
    expect(layout.cellSize).toBe(cellSize);
    expect(layout.showValues).toBe(showValues);
    expect(layout.width).toBe(layout.originX + cols * (cellSize + layout.gap) + 12);
  });
});

describe("apiErrorMessage", () => {
  it("uses the API detail when present", () => {
    expect(apiErrorMessage({ response: { data: { detail: "MQTT broker did not apply the change" } } }, "x"))
      .toBe("MQTT broker did not apply the change");
  });

  it.each([new Error("network"), { response: { data: { detail: [{ msg: "x" }] } } }, null])(
    "falls back otherwise (%#)", (err) => {
      expect(apiErrorMessage(err, "Failed")).toBe("Failed");
    });
});
