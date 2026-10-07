import { useParams } from "react-router-dom";
import FieldInference from "../components/Fields/FieldInference";

export default function InferencePage() {
  const { fieldId } = useParams<{ fieldId: string }>();
  const id = parseInt(fieldId || "0", 10);

  if (!id) {
    return <div>Invalid field ID.</div>;
  }

  return <FieldInference fieldId={id} />;
}
