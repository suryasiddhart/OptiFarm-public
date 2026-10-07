import { Layout, Typography } from "antd";
import RegisterForm from "../components/Auth/RegisterForm";

const { Content } = Layout;
const { Title } = Typography;

export default function RegisterPage() {
  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <Content
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            background: "#fff",
            borderRadius: 12,
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            padding: "24px 0",
            width: "100%",
            maxWidth: 440,
          }}
        >
          <div style={{ textAlign: "center", marginBottom: 8 }}>
            <Title level={3}>🌾 OptiFarm</Title>
          </div>
          <RegisterForm />
        </div>
      </Content>
    </Layout>
  );
}
