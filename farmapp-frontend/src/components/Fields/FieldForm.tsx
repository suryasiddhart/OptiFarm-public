import { useState } from "react"; // removed {useEffect} since it's not needed here
import {
  Form,
  InputNumber,
  Input,
  Button,
  Typography,
  message,
  Card,
  Row,
  Col,
} from "antd";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { fieldsApi } from "../../api/fieldsApi";
import type { FieldCreatePayload } from "../../types";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix Leaflet default marker icon issue
import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

const { Title } = Typography;

interface LocationMarkerProps {
  onLocationChange: (lat: number, lng: number) => void;
  initialLat?: number;
  initialLng?: number;
}

function LocationMarker({
  onLocationChange,
  initialLat,
  initialLng,
}: LocationMarkerProps) {
  const [position, setPosition] = useState<[number, number] | null>(
    initialLat && initialLng ? [initialLat, initialLng] : null
  );

  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng;
      setPosition([lat, lng]);
      onLocationChange(lat, lng);
    },
  });

  return position ? <Marker position={position} /> : null;
}

interface FieldFormProps {
  onFieldCreated?: (fieldId: number) => void;
}

export default function FieldForm({ onFieldCreated }: FieldFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [lat, setLat] = useState<number>(20.5937); // Default: India center
  const [lng, setLng] = useState<number>(78.9629);
  const { user } = useAuth();
  const navigate = useNavigate();

  // Changing the crop type clears the (now possibly mismatched) subtype
  const handleCropTypeChange = () => {
    form.setFieldValue("cropsubtype", undefined);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!user) {
      message.error("You must be logged in to add a field.");
      return;
    }

    // The backend assigns the owner from the JWT
    const payload: FieldCreatePayload = {
      fieldlength: values.fieldlength as number,
      fieldbreadth: values.fieldbreadth as number,
      croptype: values.croptype as string,
      cropsubtype: values.cropsubtype as string,
      cropinterval: values.cropinterval as number,
      fieldlat: lat,
      fieldlong: lng,
      soildata: values.soildata
        ? JSON.parse(values.soildata as string)
        : undefined,
      labels: values.labels ? JSON.parse(values.labels as string) : undefined,
    };

    setLoading(true);
    try {
      const field = await fieldsApi.create(payload);
      message.success("Field registered successfully!");
      if (onFieldCreated) {
        onFieldCreated(field.fieldid);
      } else {
        navigate(`/fields/${field.fieldid}/inference`);
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(
        error.response?.data?.detail || "Failed to register field."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <Title level={4}>Register New Field</Title>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ cropinterval: 1.0 }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="fieldlength"
              label="Field Length (meters)"
              rules={[
                { required: true, message: "Enter field length" },
                { type: "number", min: 1, message: "Must be > 0" },
              ]}
            >
              <InputNumber
                style={{ width: "100%" }}
                placeholder="e.g. 100"
                min={1}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="fieldbreadth"
              label="Field Breadth (meters)"
              rules={[
                { required: true, message: "Enter field breadth" },
                { type: "number", min: 1, message: "Must be > 0" },
              ]}
            >
              <InputNumber
                style={{ width: "100%" }}
                placeholder="e.g. 50"
                min={1}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="croptype"
              label="Crop Type"
              rules={[{ required: true, message: "Select crop type" }]}
            >
              <Input
                placeholder="e.g. Rice, Wheat, Cotton"
                onChange={handleCropTypeChange}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              name="cropsubtype"
              label="Crop Subtype"
              rules={[{ required: true, message: "Enter crop subtype" }]}
            >
              <Input placeholder="e.g. Basmati, Bt Cotton" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="cropinterval"
          label="Crop Interval / Spacing (meters)"
          rules={[
            { required: true, message: "Enter crop spacing" },
            { type: "number", min: 0.1, message: "Must be > 0.1" },
          ]}
        >
          <InputNumber
            style={{ width: "100%" }}
            placeholder="e.g. 1.0"
            min={0.1}
            step={0.1}
          />
        </Form.Item>

        <Form.Item label="Pin Field Location (click on map)">
          <Card bodyStyle={{ padding: 0 }}>
            <div style={{ height: 300, width: "100%" }}>
              <MapContainer
                center={[lat, lng]}
                zoom={5}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <LocationMarker
                  onLocationChange={(newLat, newLng) => {
                    setLat(newLat);
                    setLng(newLng);
                  }}
                  initialLat={lat}
                  initialLng={lng}
                />
              </MapContainer>
            </div>
          </Card>
          <Typography.Text type="secondary" style={{ marginTop: 4, display: "block" }}>
            Lat: {lat.toFixed(6)}, Lng: {lng.toFixed(6)}
          </Typography.Text>
        </Form.Item>

        <Form.Item name="soildata" label="Soil Data (JSON, optional)">
          <Input.TextArea
            rows={3}
            placeholder='e.g. {"ph": 6.5, "type": "loamy", "nitrogen": "high"}'
          />
        </Form.Item>

        <Form.Item name="labels" label="Labels (JSON, optional)">
          <Input.TextArea
            rows={2}
            placeholder='e.g. {"zone": "north", "notes": "near water source"}'
          />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block size="large">
            Register Field
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}
