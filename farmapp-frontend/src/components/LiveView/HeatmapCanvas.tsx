import { useRef, useEffect, useCallback } from "react";
import { moistureToColor, moistureLabel } from "../../utils/heatmapColor";
import type { SensorGrid } from "../../types";

interface HeatmapCanvasProps {
  grid: SensorGrid;
  fieldLength: number;
  fieldBreadth: number;
}

export default function HeatmapCanvas({
  grid,
  fieldLength,
  fieldBreadth,
}: HeatmapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const CELL_SIZE = 60;
  const PADDING = 20;
  const GAP = 2;

  const canvasWidth = grid.cols * (CELL_SIZE + GAP) + PADDING * 2;
  const canvasHeight = grid.rows * (CELL_SIZE + GAP) + PADDING * 2;

  const drawGrid = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background
    ctx.fillStyle = "#f5f5f5";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw each cell
    for (let r = 0; r < grid.rows; r++) {
      for (let c = 0; c < grid.cols; c++) {
        const cell = grid.cells[r]?.[c];
        const x = PADDING + c * (CELL_SIZE + GAP);
        const y = PADDING + r * (CELL_SIZE + GAP);

        const color = moistureToColor(cell?.moisture ?? null);

        // Draw cell rectangle
        ctx.fillStyle = color;
        ctx.fillRect(x, y, CELL_SIZE, CELL_SIZE);

        // Draw border
        ctx.strokeStyle = "#e0e0e0";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, CELL_SIZE, CELL_SIZE);

        // Draw moisture value text if available
        if (cell?.moisture !== null && cell?.moisture !== undefined) {
          ctx.fillStyle = "#fff";
          ctx.font = "bold 14px sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(
            `${Math.round(cell.moisture)}%`,
            x + CELL_SIZE / 2,
            y + CELL_SIZE / 2
          );
        } else {
          ctx.fillStyle = "#999";
          ctx.font = "11px sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("N/A", x + CELL_SIZE / 2, y + CELL_SIZE / 2);
        }
      }
    }

    // Draw dimension labels
    ctx.fillStyle = "#333";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(
      `${fieldLength}m`,
      canvas.width / 2,
      canvas.height - 5
    );

    // Rotate and draw breadth label
    ctx.save();
    ctx.translate(5, canvas.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(`${fieldBreadth}m`, 0, 0);
    ctx.restore();
  }, [grid, fieldLength, fieldBreadth]);

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

    // Calculate which cell the mouse is over
    const col = Math.floor((mouseX - PADDING) / (CELL_SIZE + GAP));
    const row = Math.floor((mouseY - PADDING) / (CELL_SIZE + GAP));

    if (row >= 0 && row < grid.rows && col >= 0 && col < grid.cols) {
      const cell = grid.cells[row][col];
      if (cell) {
        tooltip.style.display = "block";
        tooltip.style.left = `${e.clientX - rect.left + 10}px`;
        tooltip.style.top = `${e.clientY - rect.top - 40}px`;
        tooltip.innerHTML = `
          <strong>Cell [${row + 1}, ${col + 1}]</strong><br/>
          Moisture: ${cell.moisture !== null ? Math.round(cell.moisture) + "%" : "N/A"}<br/>
          Status: ${moistureLabel(cell.moisture)}<br/>
          ${cell.deviceid ? `Device: ${cell.deviceid}<br/>` : ""}
          ${cell.timestamp ? `Time: ${new Date(cell.timestamp).toLocaleTimeString()}` : ""}
        `;
        return;
      }
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
        width={canvasWidth}
        height={canvasHeight}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          border: "1px solid #d9d9d9",
          borderRadius: 8,
          cursor: "crosshair",
        }}
      />
      <div
        ref={tooltipRef}
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
