import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getWorkflows } from "../api/workflows";
import { getRuns } from "../api/runs";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";

function StatCard({ label, value, color }) {
  return (
    <div className="card" style={{ textAlign: "center" }}>
      <div
        style={{
          fontSize: 32,
          fontWeight: 700,
          fontFamily: "var(--font-display)",
          color: color || "var(--color-accent)",
        }}
      >
        {value}
      </div>
      <div style={{ color: "var(--color-text-muted)", fontSize: 13, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [workflows, setWorkflows] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getWorkflows(), getRuns()])
      .then(([wf, r]) => {
        setWorkflows(wf);
        setRuns(r.slice(0, 10));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  const completedRuns = runs.filter((r) => r.status === "completed").length;
  const failedRuns = runs.filter((r) => r.status === "failed").length;
  const totalCost = runs.reduce((s, r) => s + (r.total_cost_usd || 0), 0);

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      <div className="grid-2" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", marginBottom: 32 }}>
        <StatCard label="Workflows" value={workflows.length} />
        <StatCard label="Completed Runs" value={completedRuns} color="var(--color-success)" />
        <StatCard label="Failed Runs" value={failedRuns} color="var(--color-error)" />
        <StatCard
          label="Total Cost"
          value={`$${totalCost.toFixed(4)}`}
          color="var(--color-warning)"
        />
      </div>

      <div className="grid-2" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {/* Workflows */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>Workflows</h2>
            <Link to="/workflows" style={{ fontSize: 13 }}>
              View all →
            </Link>
          </div>
          {workflows.length === 0 ? (
            <div className="card empty-state">
              <p>No workflows yet.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {workflows.slice(0, 5).map((wf) => (
                <Link
                  key={wf.id}
                  to={`/workflows/${wf.id}`}
                  style={{ textDecoration: "none" }}
                >
                  <div
                    className="card"
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "12px 16px",
                      cursor: "pointer",
                      transition: "border-color 0.15s",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 500, color: "var(--color-text)" }}>
                        {wf.name}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {wf.trigger_type} · v{wf.current_version}
                      </div>
                    </div>
                    <StatusBadge status={wf.is_active ? "active" : "inactive"} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Runs */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>Recent Runs</h2>
            <Link to="/runs" style={{ fontSize: 13 }}>
              View all →
            </Link>
          </div>
          {runs.length === 0 ? (
            <div className="card empty-state">
              <p>No runs yet.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {runs.map((run) => (
                <Link
                  key={run.id}
                  to={`/runs/${run.id}`}
                  style={{ textDecoration: "none" }}
                >
                  <div
                    className="card"
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "12px 16px",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 11,
                          color: "var(--color-text-muted)",
                        }}
                      >
                        {run.id.slice(0, 8)}...
                      </div>
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {run.trigger_source} · ${(run.total_cost_usd || 0).toFixed(5)}
                      </div>
                    </div>
                    <StatusBadge status={run.status} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}