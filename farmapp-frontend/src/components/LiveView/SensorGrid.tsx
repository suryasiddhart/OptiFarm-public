import { Typography, Row, Col, Card, Tag } from "antd";
//import { moistureToColor, moistureLabel } from "../../utils/heatmapColor";
import type { SensorGrid } from "../../types";

const { Text } = Typography;

interface SensorGridInfoProps {
  grid: SensorGrid;
  fieldLength: number;
  fieldBreadth: number;
}

export default function SensorGridInfo({
  grid,
  fieldLength,
  fieldBreadth,
}: SensorGridInfoProps) {
  const totalCells = grid.rows * grid.cols;
  const cellsWithData = grid.cells
    .flat()
    .filter((c) => c.moisture !== null).length;

  return (
    <Card title="📐 Sensor Grid Information" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 8]}>
        <Col span={8}>
          <Text strong>Grid Size:</Text>{" "}
          <Text>
            {grid.rows} × {grid.cols}
          </Text>
        </Col>
        <Col span={8}>
          <Text strong>Total Cells:</Text>{" "}
          <Tag>{totalCells}</Tag>
        </Col>
        <Col span={8}>
          <Text strong>With Data:</Text>{" "}
          <Tag color={cellsWithData > 0 ? "green" : "default"}>
            {cellsWithData} / {totalCells}
          </Tag>
        </Col>
        <Col span={8}>
          <Text strong>Field Size:</Text>{" "}
          <Text>
            {fieldLength}m × {fieldBreadth}m
          </Text>
        </Col>
        <Col span={8}>
          <Text strong>Cell Size:</Text>{" "}
          <Text>
            ~{(fieldLength / grid.rows).toFixed(1)}m ×{" "}
            {(fieldBreadth / grid.cols).toFixed(1)}m
          </Text>
        </Col>
      </Row>

      <div style={{ marginTop: 12 }}>
        <Text strong>Legend:</Text>
        <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
          {[
            { color: "#1b5e20", label: "Very Wet (80-100%)" },
            { color: "#4caf50", label: "Moist (60-80%)" },
            { color: "#ffeb3b", label: "Moderate (40-60%)" },
            { color: "#ff9800", label: "Low (20-40%)" },
            { color: "#f44336", label: "Dry (0-20%)" },
            { color: "#e0e0e0", label: "No Data" },
          ].map((item) => (
            <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div
                style={{
                  width: 16,
                  height: 16,
                  backgroundColor: item.color,
                  borderRadius: 3,
                  border: "1px solid #ccc",
                }}
              />
              <Text style={{ fontSize: 12 }}>{item.label}</Text>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
