import { useState } from "react";

function formatValue(value, indent = 0) {
  if (value === null) return <span style={{ color: "#94a3b8" }}>null</span>;
  if (typeof value === "boolean")
    return <span style={{ color: "#f472b6" }}>{String(value)}</span>;
  if (typeof value === "number")
    return <span style={{ color: "#fb923c" }}>{value}</span>;
  if (typeof value === "string")
    return <span style={{ color: "#86efac" }}>"{value}"</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span style={{ color: "#94a3b8" }}>[]</span>;
    return (
      <span>
        {"["}
        {value.map((v, i) => (
          <div key={i} style={{ marginLeft: 16 }}>
            {formatValue(v, indent + 1)}
            {i < value.length - 1 ? "," : ""}
          </div>
        ))}
        {"]"}
      </span>
    );
  }
  if (typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 0) return <span style={{ color: "#94a3b8" }}>{"{}"}</span>;
    return (
      <span>
        {"{"}
        {keys.map((k, i) => (
          <div key={k} style={{ marginLeft: 16 }}>
            <span style={{ color: "#93c5fd" }}>"{k}"</span>
            {": "}
            {formatValue(value[k], indent + 1)}
            {i < keys.length - 1 ? "," : ""}
          </div>
        ))}
        {"}"}
      </span>
    );
  }
  return <span>{String(value)}</span>;
}

export default function JsonViewer({ data, maxHeight = 300 }) {
  const [expanded, setExpanded] = useState(false);

  if (!data) return <span style={{ color: "var(--color-text-muted)" }}>—</span>;

  return (
    <div style={{ position: "relative" }}>
      <pre
        style={{
          background: "#0a0c12",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          padding: "12px",
          fontFamily: "var(--font-mono)",
          fontSize: "12px",
          lineHeight: 1.6,
          overflow: "auto",
          maxHeight: expanded ? "none" : maxHeight,
          color: "var(--color-text)",
        }}
      >
        {formatValue(data)}
      </pre>
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          style={{
            position: "absolute",
            bottom: 8,
            right: 8,
            background: "var(--color-surface-2)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-muted)",
            borderRadius: "var(--radius-sm)",
            padding: "2px 8px",
            fontSize: "11px",
          }}
        >
          expand
        </button>
      )}
    </div>
  );
}