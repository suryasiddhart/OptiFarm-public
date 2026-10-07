import { useState, useEffect, useRef } from "react";
import { Spin, Result, Button, Typography, Card, Descriptions, Tag } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { fieldsApi } from "../../api/fieldsApi";
import type { Field } from "../../types";

const { Title, Text } = Typography;

interface FieldInferenceProps {
  fieldId: number;
}

export default function FieldInference({ fieldId }: FieldInferenceProps) {
  const [field, setField] = useState<Field | null>(null);
  const [loading, setLoading] = useState(true);
  const [inferenceFound, setInferenceFound] = useState<boolean | null>(null);
  const [timeoutReached, setTimeoutReached] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const startTime = Date.now();
    const MAX_WAIT_MS = 10000; // 10 seconds
    const POLL_INTERVAL_MS = 2000; // every 2 seconds

    const pollInference = async () => {
      try {
        const fieldData = await fieldsApi.getById(fieldId);
        setField(fieldData);

        if (fieldData.inference) {
          // Inference found!
          setInferenceFound(true);
          setLoading(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        } else if (Date.now() - startTime >= MAX_WAIT_MS) {
          // Timeout reached
          setTimeoutReached(true);
          setInferenceFound(false);
          setLoading(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }
      } catch {
        // If fetch fails, keep polling until timeout
        if (Date.now() - startTime >= MAX_WAIT_MS) {
          setTimeoutReached(true);
          setInferenceFound(false);
          setLoading(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }
      }
    };

    // Initial fetch
    pollInference();

    // Start polling
    pollingRef.current = setInterval(pollInference, POLL_INTERVAL_MS);

    // Cleanup on unmount
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [fieldId]);

  // Loading state
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <Spin size="large" />
        <Title level={4} style={{ marginTop: 24 }}>
          Processing your field data...
        </Title>
        <Text type="secondary">
          Analyzing field dimensions, crop type, and location to generate
          recommendations.
        </Text>
        <br />
        <Text type="secondary" style={{ marginTop: 8, display: "block" }}>
          This should take just a moment.
        </Text>
      </div>
    );
  }

  // Inference found
  if (inferenceFound && field?.inference) {
    return (
      <div style={{ maxWidth: 700, margin: "0 auto", padding: "20px 0" }}>
        <Result
          status="success"
          icon={<CheckCircleOutlined style={{ color: "#52c41a" }} />}
          title="Field Analysis Complete!"
          subTitle="Here are the recommendations for your field."
        />

        <Card title="📊 Field Inference Results" style={{ marginBottom: 16 }}>
          <Descriptions column={1} bordered size="small">
            {Object.entries(field.inference).map(([key, value]) => (
              <Descriptions.Item label={key} key={key}>
                {typeof value === "object"
                  ? JSON.stringify(value, null, 2)
                  : String(value)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </Card>

        <Card title="📋 Field Summary" style={{ marginBottom: 24 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label="Crop">
              {field.croptype} / {field.cropsubtype}
            </Descriptions.Item>
            <Descriptions.Item label="Dimensions">
              {field.fieldlength}m × {field.fieldbreadth}m
            </Descriptions.Item>
            <Descriptions.Item label="Crop Spacing">
              {field.cropinterval}m
            </Descriptions.Item>
            <Descriptions.Item label="Location">
              {field.fieldlat.toFixed(4)}, {field.fieldlong.toFixed(4)}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Button
          type="primary"
          size="large"
          block
          onClick={() => navigate("/fields")}
        >
          Accept & Continue to Fields
        </Button>
      </div>
    );
  }

  // No inference found after timeout
  return (
    <div style={{ maxWidth: 500, margin: "0 auto", padding: "40px 0" }}>
      <Result
        status="warning"
        icon={<CloseCircleOutlined style={{ color: "#faad14" }} />}
        title="No Inference Data Available"
        subTitle={
          timeoutReached
            ? "We waited 10 seconds but no inference data was found for this field. The inference may be generated later by the backend."
            : "Inference data is not available for this field."
        }
        extra={
          <div style={{ marginTop: 16 }}>
            <Tag color="blue">Field #{fieldId}</Tag>
            <Tag color="default">Inference: Pending</Tag>
            <br />
            <br />
            <Button
              type="primary"
              size="large"
              onClick={() => navigate("/fields")}
            >
              Back to Fields
            </Button>
          </div>
        }
      />
    </div>
  );
}
