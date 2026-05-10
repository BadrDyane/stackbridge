import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRuns } from "../api/runs";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";

export default function RunsPage() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRuns().then(setRuns).finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  return (
    <div className="page">
      <h1 className="page-title">Runs</h1>

      {runs.length === 0 ? (
        <div className="card empty-state">
          <h3>No runs yet</h3>
          <p>Trigger a workflow to see runs here.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr
                style={{
                  background: "var(--color-surface-2)",
                  borderBottom: "1px solid var(--color-border)",
                }}
              >
                {["Run ID", "Workflow", "Trigger", "Tokens", "Cost", "Status", ""].map(
                  (h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 16px",
                        textAlign: "left",
                        fontSize: 12,
                        color: "var(--color-text-muted)",
                        fontWeight: 500,
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr
                  key={run.id}
                  style={{
                    borderBottom:
                      i < runs.length - 1
                        ? "1px solid var(--color-border)"
                        : "none",
                  }}
                >
                  <td
                    style={{
                      padding: "12px 16px",
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {run.id.slice(0, 8)}...
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 13 }}>
                    {run.workflow_id.slice(0, 8)}...
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 13 }}>
                    {run.trigger_source}
                    {run.is_dry_run && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: 11,
                          color: "var(--color-warning)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        dry
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 13 }}>
                    {run.total_tokens}
                  </td>
                  <td
                    style={{
                      padding: "12px 16px",
                      fontSize: 13,
                      color: "var(--color-warning)",
                    }}
                  >
                    ${Number(run.total_cost_usd).toFixed(5)}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <StatusBadge status={run.status} />
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <Link to={`/runs/${run.id}`} style={{ fontSize: 13 }}>
                      Inspect →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}