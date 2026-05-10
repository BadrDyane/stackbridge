import { useEffect, useState } from "react";
import { getIntegrations, getAuthUrl, testIntegration, deleteIntegration } from "../api/integrations";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";

const PLATFORMS = [
  { id: "gmail", label: "Gmail", icon: "✉️", description: "Connect Gmail as a trigger source" },
  { id: "slack", label: "Slack", icon: "💬", description: "Post messages to Slack channels" },
  { id: "notion", label: "Notion", icon: "📝", description: "Create Notion pages as actions" },
];

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState({});
  const [testResults, setTestResults] = useState({});

  useEffect(() => {
    getIntegrations().then(setIntegrations).finally(() => setLoading(false));

    // Check for connection success in URL
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) {
      window.history.replaceState({}, "", "/integrations");
      getIntegrations().then(setIntegrations);
    }
  }, []);

  async function handleConnect(platform) {
    try {
      const data = await getAuthUrl(platform);
      window.location.href = data.auth_url;
    } catch (e) {
      alert(e.message);
    }
  }

  async function handleTest(id) {
    setTesting((t) => ({ ...t, [id]: true }));
    try {
      const result = await testIntegration(id);
      setTestResults((r) => ({ ...r, [id]: { ok: true, ...result } }));
    } catch (e) {
      setTestResults((r) => ({ ...r, [id]: { ok: false, error: e.message } }));
    } finally {
      setTesting((t) => ({ ...t, [id]: false }));
    }
  }

  async function handleDelete(id) {
    if (!confirm("Disconnect this integration?")) return;
    await deleteIntegration(id);
    setIntegrations((prev) => prev.filter((i) => i.id !== id));
  }

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  const connectedPlatforms = new Set(integrations.map((i) => i.platform));

  return (
    <div className="page">
      <h1 className="page-title">Integrations</h1>

      {/* Connect new */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12, color: "var(--color-text-muted)" }}>
          Available
        </h2>
        <div style={{ display: "flex", gap: 12 }}>
          {PLATFORMS.map((p) => (
            <div
              key={p.id}
              className="card"
              style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}
            >
              <div style={{ fontSize: 24 }}>{p.icon}</div>
              <div style={{ fontWeight: 600 }}>{p.label}</div>
              <div style={{ fontSize: 12, color: "var(--color-text-muted)", flex: 1 }}>
                {p.description}
              </div>
              {connectedPlatforms.has(p.id) ? (
                <StatusBadge status="active" />
              ) : (
                <button
                  className="btn-primary"
                  onClick={() => handleConnect(p.id)}
                  style={{ fontSize: 13 }}
                >
                  Connect
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Connected */}
      <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12, color: "var(--color-text-muted)" }}>
        Connected ({integrations.length})
      </h2>

      {integrations.length === 0 ? (
        <div className="card empty-state">
          <h3>No integrations connected</h3>
          <p>Connect a platform above to get started.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {integrations.map((integration) => (
            <div
              key={integration.id}
              className="card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "14px 20px",
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>
                  {integration.display_name}
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  {integration.platform} · {integration.scopes?.join(", ") || "no scopes"}
                </div>
              </div>

              {testResults[integration.id] && (
                <span
                  style={{
                    fontSize: 12,
                    color: testResults[integration.id].ok
                      ? "var(--color-success)"
                      : "var(--color-error)",
                  }}
                >
                  {testResults[integration.id].ok ? "✓ Valid" : "✗ Failed"}
                </span>
              )}

              <StatusBadge status={integration.is_active ? "active" : "inactive"} />

              <button
                className="btn-ghost"
                onClick={() => handleTest(integration.id)}
                disabled={testing[integration.id]}
                style={{ fontSize: 13 }}
              >
                {testing[integration.id] ? "Testing..." : "Test"}
              </button>

              <button
                className="btn-danger"
                onClick={() => handleDelete(integration.id)}
                style={{ fontSize: 13 }}
              >
                Disconnect
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}