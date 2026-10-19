/**
 * Geometry of the moisture heatmap canvas: a rows x cols matrix with 1-based
 * row numbers down the left and column numbers across the top, so cell
 * m<row>_<col> sits at that row and column.
 */
export interface HeatmapLayout {
  rows: number;
  cols: number;
  cellSize: number;
  gap: number;
  originX: number; // left edge of column 1
  originY: number; // top edge of row 1
  width: number;
  height: number;
  showValues: boolean; // cells are big enough to print the value
}

const PADDING = 12;
const LABEL_SPACE = 28; // room for the row/column numbers
const GAP = 2;

export function heatmapLayout(rows: number, cols: number): HeatmapLayout {
  const largest = Math.max(rows, cols);
  // Shrink cells for big grids so the matrix stays scrollable rather than huge
  const cellSize = largest <= 12 ? 60 : largest <= 30 ? 40 : 24;
  const originX = PADDING + LABEL_SPACE;
  const originY = PADDING + LABEL_SPACE;
  return {
    rows,
    cols,
    cellSize,
    gap: GAP,
    originX,
    originY,
    width: originX + cols * (cellSize + GAP) + PADDING,
    height: originY + rows * (cellSize + GAP) + PADDING,
    showValues: cellSize >= 40,
  };
}

/** Top-left corner of a cell (zero-based row/col). */
export function cellOrigin(layout: HeatmapLayout, row: number, col: number): { x: number; y: number } {
  return {
    x: layout.originX + col * (layout.cellSize + layout.gap),
    y: layout.originY + row * (layout.cellSize + layout.gap),
  };
}

/** Zero-based cell under a canvas point, or null outside the matrix. */
export function cellAtPoint(layout: HeatmapLayout, x: number, y: number): { row: number; col: number } | null {
  const step = layout.cellSize + layout.gap;
  const col = Math.floor((x - layout.originX) / step);
  const row = Math.floor((y - layout.originY) / step);
  if (row < 0 || row >= layout.rows || col < 0 || col >= layout.cols) return null;
  return { row, col };
}
