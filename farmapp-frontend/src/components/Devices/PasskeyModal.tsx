import { Alert, Button, Descriptions, Modal, Typography } from "antd";
import type { DeviceCredentials } from "../../types";

const { Text } = Typography;

interface PasskeyModalProps {
  // null = closed. The passkey only lives here, in memory, until the user closes
  // the dialog; it is never stored and can't be fetched again.
  credentials: DeviceCredentials | null;
  // "created" after Add device, "rotated" after Rotate passkey
  reason: "created" | "rotated";
  onClose: () => void;
}

export default function PasskeyModal({ credentials, reason, onClose }: PasskeyModalProps) {
  return (
    <Modal
      open={credentials !== null}
      title={reason === "created" ? "Device added" : "Passkey rotated"}
      // Only the explicit button closes it, so the passkey isn't lost by a stray click
      closable={false}
      mask={{ closable: false }}
      keyboard={false}
      destroyOnHidden
      width={640}
      footer={
        <Button type="primary" onClick={onClose}>
          I&apos;ve saved the passkey
        </Button>
      }
    >
      {credentials && (
        <>
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            title="This passkey is shown only once."
            description={
              reason === "rotated"
                ? "Store it now and update the device: the previous passkey has stopped working. It can't be retrieved later; rotate again to get a new one."
                : "Store it now and configure it on the device. It can't be retrieved later; rotate the passkey to get a new one."
            }
          />
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Device name">{credentials.devicename}</Descriptions.Item>
            <Descriptions.Item label="Device ID (MQTT username)">
              <Text code copyable>
                {credentials.deviceid}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Passkey (MQTT password)">
              <Text code copyable data-testid="device-passkey">
                {credentials.passkey}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="MQTT topic">
              <Text code copyable>
                {credentials.mqtt_topic}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Modal>
  );
}
