import { useState, useEffect, useCallback } from "react";
import { Alert, Button, Modal, Spin, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { moistureApi } from "../../api/moistureApi";
import { calculateGrid, mapReadingsToGrid } from "../../utils/gridCalculator";
import { apiErrorMessage } from "../../utils/apiError";
import HeatmapCanvas from "./HeatmapCanvas";
import SensorGridInfo from "./SensorGrid";
import type { Field, SensorGrid } from "../../types";

const { Text } = Typography;

const REFRESH_MS = 15000;

interface LiveViewModalProps {
  field: Field;
  open: boolean;
  onClose: () => void;
}

/**
 * Live moisture grid of one field. Readings ({ m<row>_<col>: value }) are
 * placed in the matrix by their key; each cell shows its latest value.
 * Polls every 15 s only while open.
 */
export default function LiveViewModal({ field, open, onClose }: LiveViewModalProps) {
  const [grid, setGrid] = useState<SensorGrid | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const empty = calculateGrid(field.fieldlength, field.fieldbreadth, field.cropinterval);
      const readings = await moistureApi.getByField(field.fieldid, 1000);
      setGrid(mapReadingsToGrid(empty, readings));
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "Failed to load moisture data."));
    } finally {
      setLoading(false);
    }
  }, [field]);

  useEffect(() => {
    if (!open) return;
    // State updates only happen once the request resolves
    const initialLoad = setTimeout(fetchData, 0);
    const polling = setInterval(fetchData, REFRESH_MS);
    return () => {
      clearTimeout(initialLoad);
      clearInterval(polling);
    };
  }, [open, fetchData]);

  return (
    <Modal
      open={open}
      title={`Live View — Field #${field.fieldid} (${field.croptype} / ${field.cropsubtype})`}
      onCancel={onClose}
      width="90vw"
      style={{ top: 24 }}
      destroyOnHidden
      footer={<Button onClick={onClose}>Close</Button>}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <Alert
          type="error"
          showIcon
          title="Error"
          description={error}
          action={
            <Button onClick={fetchData} icon={<ReloadOutlined />}>
              Retry
            </Button>
          }
        />
      ) : (
        grid && (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <Text type="secondary">
                Rows run along the length ({field.fieldlength} m), columns along the breadth (
                {field.fieldbreadth} m). Cell m&lt;row&gt;_&lt;col&gt; is shown at that row and column.
              </Text>
              <div style={{ textAlign: "right", whiteSpace: "nowrap", marginLeft: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Auto-refreshes every 15s · Last updated: {lastUpdated}
                </Text>
                <br />
                <Button size="small" icon={<ReloadOutlined />} onClick={fetchData} style={{ marginTop: 4 }}>
                  Refresh now
                </Button>
              </div>
            </div>

            <SensorGridInfo grid={grid} fieldLength={field.fieldlength} fieldBreadth={field.fieldbreadth} />

            <div
              style={{
                overflow: "auto",
                maxHeight: "60vh",
                padding: 16,
                background: "#fff",
                borderRadius: 8,
                border: "1px solid #f0f0f0",
                textAlign: "center",
              }}
            >
              <HeatmapCanvas grid={grid} />
            </div>
          </>
        )
      )}
    </Modal>
  );
}
