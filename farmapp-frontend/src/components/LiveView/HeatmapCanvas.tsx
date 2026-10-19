import { useRef, useEffect, useCallback, useMemo } from "react";
import { moistureToColor, moistureLabel } from "../../utils/heatmapColor";
import { cellAtPoint, cellOrigin, heatmapLayout } from "../../utils/heatmapLayout";
import type { SensorGrid } from "../../types";

interface HeatmapCanvasProps {
  grid: SensorGrid;
}

/**
 * The moisture grid as a matrix: row numbers down the left, column numbers
 * across the top (both 1-based), so reading key m2_5 is drawn at row 2,
 * column 5. Rows run along the field's length, columns along its breadth.
 */
export default function HeatmapCanvas({ grid }: HeatmapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const layout = useMemo(() => heatmapLayout(grid.rows, grid.cols), [grid.rows, grid.cols]);

  const drawGrid = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f5f5f5";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const { cellSize } = layout;
    const half = cellSize / 2;

    // Column numbers across the top, row numbers down the left
    ctx.fillStyle = "#555";
    ctx.font = `${cellSize >= 40 ? 12 : 10}px sans-serif`;
    ctx.textBaseline = "middle";
    ctx.textAlign = "center";
    for (let c = 0; c < grid.cols; c++) {
      const { x } = cellOrigin(layout, 0, c);
      ctx.fillText(String(c + 1), x + half, layout.originY - 12);
    }
    ctx.textAlign = "right";
    for (let r = 0; r < grid.rows; r++) {
      const { y } = cellOrigin(layout, r, 0);
      ctx.fillText(String(r + 1), layout.originX - 6, y + half);
    }

    for (let r = 0; r < grid.rows; r++) {
      for (let c = 0; c < grid.cols; c++) {
        const cell = grid.cells[r]?.[c];
        const { x, y } = cellOrigin(layout, r, c);

        ctx.fillStyle = moistureToColor(cell?.moisture ?? null);
        ctx.fillRect(x, y, cellSize, cellSize);
        ctx.strokeStyle = "#e0e0e0";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, cellSize, cellSize);

        if (!layout.showValues) continue;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        if (cell?.moisture !== null && cell?.moisture !== undefined) {
          ctx.fillStyle = "#fff";
          ctx.font = `bold ${cellSize >= 60 ? 14 : 12}px sans-serif`;
          ctx.fillText(`${Math.round(cell.moisture)}%`, x + half, y + half);
        } else {
          ctx.fillStyle = "#999";
          ctx.font = "11px sans-serif";
          ctx.fillText("N/A", x + half, y + half);
        }
      }
    }
  }, [grid, layout]);

  useEffect(() => {
    drawGrid();
  }, [drawGrid]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    const tooltip = tooltipRef.current;
    if (!canvas || !tooltip) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const position = cellAtPoint(layout, mouseX, mouseY);
    const cell = position && grid.cells[position.row]?.[position.col];

    if (position && cell) {
      tooltip.style.display = "block";
      tooltip.style.left = `${mouseX + 10}px`;
      tooltip.style.top = `${mouseY - 40}px`;
      tooltip.innerHTML = `
        <strong>m${position.row + 1}_${position.col + 1}</strong>
        (row ${position.row + 1}, column ${position.col + 1})<br/>
        Moisture: ${cell.moisture !== null ? cell.moisture + "%" : "N/A"}<br/>
        Status: ${moistureLabel(cell.moisture)}<br/>
        ${cell.deviceid ? `Device: ${cell.deviceid}<br/>` : ""}
        ${cell.timestamp ? `Time: ${new Date(cell.timestamp).toLocaleString()}` : ""}
      `;
      return;
    }
    tooltip.style.display = "none";
  };

  const handleMouseLeave = () => {
    if (tooltipRef.current) {
      tooltipRef.current.style.display = "none";
    }
  };

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <canvas
        ref={canvasRef}
        width={layout.width}
        height={layout.height}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        aria-label={`Soil moisture grid, ${grid.rows} rows by ${grid.cols} columns`}
        role="img"
        data-testid="moisture-heatmap"
        style={{
          border: "1px solid #d9d9d9",
          borderRadius: 8,
          cursor: "crosshair",
        }}
      />
      <div
        ref={tooltipRef}
        data-testid="moisture-heatmap-tooltip"
        style={{
          display: "none",
          position: "absolute",
          background: "rgba(0,0,0,0.8)",
          color: "#fff",
          padding: "8px 12px",
          borderRadius: 6,
          fontSize: 12,
          pointerEvents: "none",
          whiteSpace: "nowrap",
          zIndex: 1000,
        }}
      />
    </div>
  );
}
