import { Table, Tag, Button, Typography, Empty, Space } from "antd";
import { PlusOutlined, EyeOutlined, ThunderboltOutlined, ApiOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { Field } from "../../types";

const { Text } = Typography;

interface FieldsTableProps {
  fields: Field[];
  loading: boolean;
  // Active devices per field id
  deviceCounts: Record<number, number>;
  onViewDevices: (field: Field) => void;
  onLiveView: (field: Field) => void;
}

export default function FieldsTable({
  fields,
  loading,
  deviceCounts,
  onViewDevices,
  onLiveView,
}: FieldsTableProps) {
  const navigate = useNavigate();

  const columns = [
    {
      title: "Field ID",
      dataIndex: "fieldid",
      key: "fieldid",
      width: 80,
    },
    {
      title: "Crop Type",
      dataIndex: "croptype",
      key: "croptype",
      render: (text: string, record: Field) => (
        <span>
          {text} / {record.cropsubtype}
        </span>
      ),
    },
    {
      title: "Dimensions",
      key: "dimensions",
      render: (_: unknown, record: Field) => (
        <Text>
          {record.fieldlength}m × {record.fieldbreadth}m
        </Text>
      ),
    },
    {
      title: "Crop Interval",
      dataIndex: "cropinterval",
      key: "cropinterval",
      render: (val: number) => `${val}m`,
    },
    {
      title: "Location",
      key: "location",
      render: (_: unknown, record: Field) => (
        <Text type="secondary">
          {record.fieldlat.toFixed(4)}, {record.fieldlong.toFixed(4)}
        </Text>
      ),
    },
    {
      title: "Inference",
      dataIndex: "inference",
      key: "inference",
      render: (inference: Record<string, unknown> | null) =>
        inference ? (
          <Tag color="green">Available</Tag>
        ) : (
          <Tag color="default">Pending</Tag>
        ),
    },
    {
      title: "Devices",
      key: "devices",
      render: (_: unknown, record: Field) => {
        const count = deviceCounts[record.fieldid] ?? 0;
        return (
          <Space size={4}>
            <Tag color={count ? "blue" : "default"} data-testid="device-count">
              {count}
            </Tag>
            <Button type="link" size="small" icon={<ApiOutlined />} onClick={() => onViewDevices(record)}>
              View devices
            </Button>
          </Space>
        );
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, record: Field) => (
        <Space>
          <Button
            type="link"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate(`/fields/${record.fieldid}/inference`)}
          >
            Inference
          </Button>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => onLiveView(record)}
          >
            Live View
          </Button>
        </Space>
      ),
    },
  ];


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
        <Typography.Title level={4} style={{ margin: 0 }}>
          My Fields
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate("/fields/add")}
          size="large"
        >
          Add Field
        </Button>
      </div>

      <Table
        dataSource={fields}
        columns={columns}
        rowKey="fieldid"
        loading={loading}
        locale={{
          emptyText: (
            <Empty description="No fields registered yet. Click 'Add Field' to get started!" />
          ),
        }}
        pagination={false}
        scroll={{ x: 900 }}
      />
    </div>
  );
}
