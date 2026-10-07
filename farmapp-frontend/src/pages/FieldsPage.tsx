import { useState, useEffect } from "react";
import { message } from "antd";
import FieldsTable from "../components/Fields/FieldsTable";
import { fieldsApi } from "../api/fieldsApi";
import type { Field } from "../types";

export default function FieldsPage() {
  const [fields, setFields] = useState<Field[]>([]);
  const [loading, setLoading] = useState(true);

  // Load fields once on mount (loading starts as true)
  useEffect(() => {
    let cancelled = false;
    const loadFields = async () => {
      try {
        const data = await fieldsApi.list();
        if (!cancelled) setFields(data);
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } };
        message.error(
          error.response?.data?.detail || "Failed to load fields."
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadFields();
    return () => {
      cancelled = true;
    };
  }, []);

  return <FieldsTable fields={fields} loading={loading} />;
}
