import { useNavigate, useLocation } from "react-router-dom";
import { Menu } from "antd";
import { UnorderedListOutlined, LogoutOutlined } from "@ant-design/icons";
import { useAuth } from "../../hooks/useAuth";

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();

  const handleMenuClick = async (key: string) => {
    if (key === "logout") {
      await logout();
      navigate("/login");
    } else {
      navigate(key);
    }
  };

  // Devices and Live View are opened per field from My Fields
  const menuItems = [
    {
      key: "/fields",
      icon: <UnorderedListOutlined />,
      label: "My Fields",
    },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      danger: true,
    },
  ];

  const selectedKey = location.pathname.startsWith("/fields") ? "/fields" : location.pathname;

  return (
    <Menu
      mode="inline"
      selectedKeys={[selectedKey]}
      items={menuItems}
      onClick={({ key }) => handleMenuClick(key)}
      style={{ height: "100%", borderRight: 0 }}
    />
  );
}
