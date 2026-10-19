import { useState } from "react";
import { Form, Input, Modal, message } from "antd";
import { devicesApi } from "../../api/devicesApi";
import { apiErrorMessage } from "../../utils/apiError";
import type { DeviceCredentials, Field } from "../../types";

interface AddDeviceModalProps {
  field: Field;
  open: boolean;
  onClose: () => void;
  // Receives the credentials (with the one-time passkey) of the new device
  onCreated: (credentials: DeviceCredentials) => void;
}

interface AddDeviceFormValues {
  devicename: string;
}

export default function AddDeviceModal({ field, open, onClose, onCreated }: AddDeviceModalProps) {
  const [form] = Form.useForm<AddDeviceFormValues>();
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (values: AddDeviceFormValues) => {
    setSaving(true);
    try {
      const credentials = await devicesApi.create({
        devicename: values.devicename.trim(),
        fieldid: field.fieldid,
      });
      form.resetFields();
      onCreated(credentials);
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "Failed to add the device."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={`Add device — Field #${field.fieldid}`}
      okText="Add device"
      confirmLoading={saving}
      onOk={() => form.submit()}
      onCancel={onClose}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit} preserve={false}>
        <Form.Item
          name="devicename"
          label="Device name"
          extra="A name to recognise the device, e.g. North corner sensor. A device ID and passkey are generated for its MQTT login."
          rules={[
            { required: true, whitespace: true, message: "Enter a device name" },
            { max: 100, message: "At most 100 characters" },
          ]}
        >
          <Input placeholder="North corner sensor" maxLength={100} autoFocus />
        </Form.Item>
      </Form>
    </Modal>
  );
}
