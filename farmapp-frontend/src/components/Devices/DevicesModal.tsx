import { useCallback, useEffect, useState } from "react";
import { Button, Empty, Modal, Popconfirm, Space, Table, Typography, message } from "antd";
import { DeleteOutlined, KeyOutlined, PlusOutlined } from "@ant-design/icons";
import { devicesApi } from "../../api/devicesApi";
import { apiErrorMessage } from "../../utils/apiError";
import AddDeviceModal from "./AddDeviceModal";
import PasskeyModal from "./PasskeyModal";
import type { Device, DeviceCredentials, Field } from "../../types";

const { Text } = Typography;

interface DevicesModalProps {
  field: Field;
  open: boolean;
  onClose: () => void;
  // Called after a device is added or deleted (e.g. to refresh device counts)
  onChange: () => void;
}

const formatTime = (value: string | null) => (value ? new Date(value).toLocaleString() : "never");

export default function DevicesModal({ field, open, onClose, onChange }: DevicesModalProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyDevice, setBusyDevice] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [credentials, setCredentials] = useState<DeviceCredentials | null>(null);
  const [credentialsReason, setCredentialsReason] = useState<"created" | "rotated">("created");

  const loadDevices = useCallback(async () => {
    setLoading(true);
    try {
      setDevices(await devicesApi.list(field.fieldid));
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "Failed to load devices."));
    } finally {
      setLoading(false);
    }
  }, [field.fieldid]);

  useEffect(() => {
    if (!open) return;
    // Deferred so no state is set synchronously inside the effect
    const initialLoad = setTimeout(loadDevices, 0);
    return () => clearTimeout(initialLoad);
  }, [open, loadDevices]);

  const showCredentials = (creds: DeviceCredentials, reason: "created" | "rotated") => {
    setCredentialsReason(reason);
    setCredentials(creds);
  };

  const handleCreated = (creds: DeviceCredentials) => {
    setAdding(false);
    showCredentials(creds, "created");
    loadDevices();
    onChange();
  };

  const handleRotate = async (device: Device) => {
    setBusyDevice(device.deviceid);
    try {
      showCredentials(await devicesApi.rotatePasskey(device.deviceid), "rotated");
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "Failed to rotate the passkey."));
    } finally {
      setBusyDevice(null);
    }
  };

  const handleDelete = async (device: Device) => {
    setBusyDevice(device.deviceid);
    try {
      await devicesApi.remove(device.deviceid);
      message.success(`Deleted ${device.devicename}`);
      await loadDevices();
      onChange();
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "Failed to delete the device."));
    } finally {
      setBusyDevice(null);
    }
  };

  const columns = [
    { title: "Name", dataIndex: "devicename", key: "devicename" },
    {
      title: "Device ID",
      dataIndex: "deviceid",
      key: "deviceid",
      render: (id: string) => <Text code>{id}</Text>,
    },
    { title: "Last seen", dataIndex: "last_seen", key: "last_seen", render: formatTime },
    { title: "Created", dataIndex: "created_at", key: "created_at", render: formatTime },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, device: Device) => (
        <Space>
          <Popconfirm
            title="Rotate passkey?"
            description="The current passkey stops working immediately; the device needs the new one."
            okText="Rotate"
            onConfirm={() => handleRotate(device)}
          >
            <Button type="link" icon={<KeyOutlined />} loading={busyDevice === device.deviceid}>
              Rotate passkey
            </Button>
          </Popconfirm>
          <Popconfirm
            title={`Delete ${device.devicename}?`}
            description="The device can no longer connect. Its past readings are kept."
            okText="Delete"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDelete(device)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} disabled={busyDevice === device.deviceid}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Modal
        open={open}
        title={`Devices — Field #${field.fieldid} (${field.croptype} / ${field.cropsubtype})`}
        onCancel={onClose}
        width={900}
        destroyOnHidden
        footer={<Button onClick={onClose}>Close</Button>}
      >
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAdding(true)}>
            Add device
          </Button>
        </div>
        <Table
          dataSource={devices}
          columns={columns}
          rowKey="deviceid"
          loading={loading}
          pagination={false}
          size="small"
          scroll={{ x: 700 }}
          locale={{ emptyText: <Empty description="No devices on this field yet." /> }}
        />
      </Modal>

      <AddDeviceModal
        field={field}
        open={adding}
        onClose={() => setAdding(false)}
        onCreated={handleCreated}
      />
      <PasskeyModal
        credentials={credentials}
        reason={credentialsReason}
        onClose={() => setCredentials(null)}
      />
    </>
  );
}
