import { useState, useEffect, useRef } from "react";
import { Input, Typography, Space } from "antd";

const { Text } = Typography;

/**
 * Client-side math challenge — a UX speed bump only, NOT a security control:
 * the API never sees or verifies it. Brute-force protection is enforced
 * server-side (nginx per-IP rate limit on /api/auth/* and per-account lockout
 * in the API).
 */
interface MathCaptchaProps {
  onValidate: (isValid: boolean) => void;
}

export default function MathCaptcha({ onValidate }: MathCaptchaProps) {
  const [num1, setNum1] = useState(0);
  const [num2, setNum2] = useState(0);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState(false);
  const initialized = useRef(false);

  const generateNew = () => {
    const a = Math.floor(Math.random() * 20) + 1;
    const b = Math.floor(Math.random() * 20) + 1;
    setNum1(a);
    setNum2(b);
    setAnswer("");
    setError(false);
    onValidate(false);
  };

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      generateNew();
    }
  }, []);

  const handleChange = (value: string) => {
    setAnswer(value);
    const parsed = parseInt(value, 10);
    if (value.length > 0) {
      if (parsed === num1 + num2) {
        setError(false);
        onValidate(true);
      } else {
        setError(true);
        onValidate(false);
      }
    } else {
      setError(false);
      onValidate(false);
    }
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Text strong>
        What is {num1} + {num2}?
      </Text>
      <Input
        placeholder="Enter the answer"
        value={answer}
        onChange={(e) => handleChange(e.target.value)}
        status={error ? "error" : answer ? "success" : undefined}
        maxLength={3}
      />
      {error && (
        <Text type="danger" style={{ fontSize: 12 }}>
          Incorrect answer. Please try again.
        </Text>
      )}
      <Text
        type="secondary"
        style={{ fontSize: 12, cursor: "pointer" }}
        onClick={generateNew}
      >
        ↻ New question
      </Text>
    </Space>
  );
}
