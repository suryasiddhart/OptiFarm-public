import { useState } from "react";
import { Form, Input, Button, Typography, message } from "antd";
import { MobileOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import MathCaptcha from "../Common/MathCaptcha";

const { Title } = Typography;

export default function LoginForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [captchaValid, setCaptchaValid] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (values: {
    mobileno: string;
    password: string;
  }) => {
    if (!captchaValid) {
      message.error("Please solve the captcha correctly.");
      return;
    }

    setLoading(true);
    try {
      await login({
        mobileno: values.mobileno,
        password: values.password,
      });
      message.success("Login successful!");
      navigate("/fields");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(
        error.response?.data?.detail || "Login failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: 400,
        margin: "0 auto",
        padding: "40px 20px",
      }}
    >
      <Title level={2} style={{ textAlign: "center", marginBottom: 32 }}>
        Login
      </Title>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        autoComplete="off"
      >
        <Form.Item
          name="mobileno"
          label="Mobile Number"
          rules={[
            { required: true, message: "Please enter your mobile number" },
            { pattern: /^\d{10}$/, message: "Enter a valid 10-digit number" },
          ]}
        >
          <Input
            prefix={<MobileOutlined />}
            placeholder="Enter mobile number"
            size="large"
            maxLength={10}
          />
        </Form.Item>

        <Form.Item
          name="password"
          label="Password"
          rules={[{ required: true, message: "Please enter your password" }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Enter password"
            size="large"
          />
        </Form.Item>

        <Form.Item label="Security Check">
          <MathCaptcha onValidate={setCaptchaValid} />
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
            size="large"
          >
            Log In
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: "center" }}>
        Don't have an account?{" "}
        <Link to="/register">Register here</Link>
      </div>
    </div>
  );
}
