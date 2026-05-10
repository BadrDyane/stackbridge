const COLORS = {
    completed: { bg: "#14532d", color: "#22c55e", label: "Completed" },
    running: { bg: "#1e3a5f", color: "#60a5fa", label: "Running" },
    pending: { bg: "#3b3209", color: "#f59e0b", label: "Pending" },
    failed: { bg: "#450a0a", color: "#ef4444", label: "Failed" },
    active: { bg: "#1e1b4b", color: "#6366f1", label: "Active" },
    inactive: { bg: "#1e293b", color: "#94a3b8", label: "Inactive" },
  };
  
  export default function StatusBadge({ status }) {
    const style = COLORS[status] || COLORS.pending;
    return (
      <span
        style={{
          background: style.bg,
          color: style.color,
          padding: "2px 10px",
          borderRadius: "999px",
          fontSize: "12px",
          fontWeight: 600,
          fontFamily: "var(--font-mono)",
          whiteSpace: "nowrap",
        }}
      >
        {style.label}
      </span>
    );
  }