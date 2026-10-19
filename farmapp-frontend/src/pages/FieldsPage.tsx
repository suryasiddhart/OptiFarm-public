import { useState, useEffect, useCallback } from "react";
import { message } from "antd";
import FieldsTable from "../components/Fields/FieldsTable";
import DevicesModal from "../components/Devices/DevicesModal";
import LiveViewModal from "../components/LiveView/LiveViewModal";
import { fieldsApi } from "../api/fieldsApi";
import { devicesApi } from "../api/devicesApi";
import { countDevicesByField } from "../utils/deviceCounts";
import { apiErrorMessage } from "../utils/apiError";
import type { Field } from "../types";

export default function FieldsPage() {
  const [fields, setFields] = useState<Field[]>([]);
  const [deviceCounts, setDeviceCounts] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [devicesField, setDevicesField] = useState<Field | null>(null);
  const [liveField, setLiveField] = useState<Field | null>(null);

  const loadDeviceCounts = useCallback(async () => {
    try {
      setDeviceCounts(countDevicesByField(await devicesApi.list()));
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "Failed to load devices."));
    }
  }, []);

  // Load fields and device counts once on mount (loading starts as true)
  useEffect(() => {
    let cancelled = false;
    const loadFields = async () => {
      try {
        const [fieldData, devices] = await Promise.all([fieldsApi.list(), devicesApi.list()]);
        if (!cancelled) {
          setFields(fieldData);
          setDeviceCounts(countDevicesByField(devices));
        }
      } catch (err: unknown) {
        message.error(apiErrorMessage(err, "Failed to load fields."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadFields();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <FieldsTable
        fields={fields}
        loading={loading}
        deviceCounts={deviceCounts}
        onViewDevices={setDevicesField}
        onLiveView={setLiveField}
      />
      {devicesField && (
        <DevicesModal
          field={devicesField}
          open
          onClose={() => setDevicesField(null)}
          onChange={loadDeviceCounts}
        />
      )}
      {liveField && <LiveViewModal field={liveField} open onClose={() => setLiveField(null)} />}
    </>
  );
}
