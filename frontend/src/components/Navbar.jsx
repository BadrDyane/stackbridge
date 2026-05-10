import { Link, useLocation } from "react-router-dom";
import { logout } from "../api/auth";

const NAV_ITEMS = [
  { path: "/", label: "Dashboard" },
  { path: "/workflows", label: "Workflows" },
  { path: "/runs", label: "Runs" },
  { path: "/integrations", label: "Integrations" },
  { path: "/cost", label: "Cost" },
  { path: "/dlq", label: "DLQ" },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav
      style={{
        background: "var(--color-surface)",
        borderBottom: "1px solid var(--color-border)",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        gap: 0,
        height: 52,
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: 18,
          color: "var(--color-accent)",
          marginRight: 32,
          letterSpacing: "-0.5px",
        }}
      >
        StackBridge
      </span>

      <div style={{ display: "flex", gap: 4, flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active =
            item.path === "/"
              ? pathname === "/"
              : pathname.startsWith(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
                color: active ? "var(--color-accent)" : "var(--color-text-muted)",
                fontWeight: active ? 600 : 400,
                background: active ? "rgba(99,102,241,0.1)" : "transparent",
                fontSize: 14,
                transition: "all 0.15s",
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

      <button
        onClick={logout}
        className="btn-ghost"
        style={{ padding: "4px 12px", fontSize: 13 }}
      >
        Sign out
      </button>
    </nav>
  );
}