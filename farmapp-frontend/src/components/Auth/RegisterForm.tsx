import { useState } from "react";
import { Form, Input, Button, Typography, message } from "antd";
import { UserOutlined, MobileOutlined, MailOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

const { Title } = Typography;

export default function RegisterForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (values: {
    firstname: string;
    lastname: string;
    mobileno: string;
    emailid?: string;
    password: string;
  }) => {
    setLoading(true);
    try {
      await register({
        firstname: values.firstname,
        lastname: values.lastname,
        mobileno: values.mobileno,
        emailid: values.emailid || undefined,
        password: values.password,
      });
      message.success("Registration successful! Please log in.");
      navigate("/login");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      message.error(
        error.response?.data?.detail || "Registration failed. Please try again."
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
        Farmer Registration
      </Title>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        autoComplete="off"
      >
        <Form.Item
          name="firstname"
          label="First Name"
          rules={[{ required: true, message: "Please enter your first name" }]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder="First name"
            size="large"
          />
        </Form.Item>

        <Form.Item
          name="lastname"
          label="Last Name"
          rules={[{ required: true, message: "Please enter your last name" }]}
        >
          <Input
            prefix={<UserOutlined />}
            placeholder="Last name"
            size="large"
          />
        </Form.Item>

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
            placeholder="10-digit mobile number"
            size="large"
            maxLength={10}
          />
        </Form.Item>

        <Form.Item name="emailid" label="Email ID (optional)">
          <Input
            prefix={<MailOutlined />}
            placeholder="email@example.com"
            size="large"
            type="email"
          />
        </Form.Item>

        <Form.Item
          name="password"
          label="Password"
          rules={[
            { required: true, message: "Please enter a password" },
            { min: 6, message: "Password must be at least 6 characters" },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Create a password"
            size="large"
          />
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
            size="large"
          >
            Register
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: "center" }}>
        Already have an account?{" "}
        <Link to="/login">Log in</Link>
      </div>
    </div>
  );
}
