import { useNavigate, useLocation } from "react-router-dom";
import { Menu } from "antd";
import {
  UnorderedListOutlined,
  HeatMapOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useAuth } from "../../hooks/useAuth";

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();  // removed {user} since it's not used

  const handleMenuClick = async (key: string) => {
    if (key === "logout") {
      await logout();
      navigate("/login");
    } else {
      navigate(key);
    }
  };

  // Extract fieldId from current path if on a field-specific page
  const fieldMatch = location.pathname.match(/\/fields\/(\d+)/);
  const currentFieldId = fieldMatch ? fieldMatch[1] : null;

  const menuItems = [
    {
      key: "/fields",
      icon: <UnorderedListOutlined />,
      label: "My Fields",
    },
    {
      key: currentFieldId ? `/fields/${currentFieldId}/live` : "/fields",
      icon: <HeatMapOutlined />,
      label: "Live View",
      disabled: !currentFieldId,
    },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      danger: true,
    },
  ];

  // Determine selected key based on current path
  const selectedKey = location.pathname.startsWith("/fields")
    ? "/fields"
    : location.pathname;

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

