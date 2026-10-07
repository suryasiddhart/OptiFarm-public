import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { Spin, Typography, Alert, Button } from "antd"; //removed {message}
import { ReloadOutlined } from "@ant-design/icons";
import { fieldsApi } from "../api/fieldsApi";
import { moistureApi } from "../api/moistureApi";
import { calculateGrid, mapReadingsToGrid } from "../utils/gridCalculator";
import HeatmapCanvas from "../components/LiveView/HeatmapCanvas";
import SensorGridInfo from "../components/LiveView/SensorGrid";
import type { Field, SensorGrid } from "../types";

const { Title, Text } = Typography;

export default function LiveViewPage() {
  const { fieldId } = useParams<{ fieldId: string }>();
  const id = parseInt(fieldId || "0", 10);

  const [field, setField] = useState<Field | null>(null);
  const [grid, setGrid] = useState<SensorGrid | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    if (!id) return;

    try {
      // Fetch field details
      const fieldData = await fieldsApi.getById(id);
      setField(fieldData);

      // Calculate grid from field dimensions
      const calculatedGrid = calculateGrid(
        fieldData.fieldlength,
        fieldData.fieldbreadth,
        fieldData.cropinterval
      );

      // Fetch moisture readings
      const readings = await moistureApi.getByField(id, 1000);

      // Map readings to grid
      const updatedGrid = mapReadingsToGrid(calculatedGrid, readings);
      setGrid(updatedGrid);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      setError(
        errorObj.response?.data?.detail || "Failed to load field data."
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Initial load
  useEffect(() => {
    if (!id) return;

    // Initial load; state is only updated after the request resolves
    const initialLoad = setTimeout(fetchData, 0);

    // Start polling every 15 seconds
    pollingRef.current = setInterval(fetchData, 15000);

    return () => {
      clearTimeout(initialLoad);
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [id, fetchData]);

  if (!id) {
    return <div>Invalid field ID.</div>;
  }

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <Spin size="large" />
        <Title level={4} style={{ marginTop: 24 }}>
          Loading field data...
        </Title>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Error"
        description={error}
        type="error"
        showIcon
        action={
          <Button onClick={fetchData} icon={<ReloadOutlined />}>
            Retry
          </Button>
        }
      />
    );
  }

  if (!field || !grid) {
    return <div>Field not found.</div>;
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0 }}>
            Live View — Field #{field.fieldid}
          </Title>
          <Text type="secondary">
            {field.croptype} / {field.cropsubtype} | {field.fieldlength}m ×{" "}
            {field.fieldbreadth}m
          </Text>
        </div>
        <div style={{ textAlign: "right" }}>
          <Text type="secondary" style={{ display: "block", fontSize: 12 }}>
            Auto-refreshes every 15s
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Last updated: {lastUpdated}
          </Text>
          <br />
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={fetchData}
            style={{ marginTop: 4 }}
          >
            Refresh Now
          </Button>
        </div>
      </div>

      <SensorGridInfo
        grid={grid}
        fieldLength={field.fieldlength}
        fieldBreadth={field.fieldbreadth}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: 16,
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #f0f0f0",
        }}
      >
        <HeatmapCanvas
          grid={grid}
          fieldLength={field.fieldlength}
          fieldBreadth={field.fieldbreadth}
        />
      </div>
    </div>
  );
}
