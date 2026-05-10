import { useEffect, useState } from "react";
import { getDLQ, resolveDLQ } from "../api/integrations";
import LoadingSpinner from "../components/LoadingSpinner";

export default function DLQPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState({});

  useEffect(() => {
    getDLQ().then(setEntries).finally(() => setLoading(false));
  }, []);

  async function handleResolve(id) {
    setResolving((r) => ({ ...r, [id]: true }));
    try {
      await resolveDLQ(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (e) {
      alert(e.message);
    } finally {
      setResolving((r) => ({ ...r, [id]: false }));
    }
  }

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  return (
    <div className="page">
      <h1 className="page-title">Dead Letter Queue</h1>
      <p style={{ color: "var(--color-text-muted)", marginBottom: 24, fontSize: 14 }}>
        Runs that failed after all retries are listed here. Resolve them manually
        after investigation.
      </p>

      {entries.length === 0 ? (
        <div className="card empty-state">
          <h3>Dead Letter Queue is empty</h3>
          <p>All runs are healthy. No failed entries requiring attention.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {entries.map((entry) => (
            <div key={entry.id} className="card">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: 12,
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--color-text-muted)",
                    }}
                  >
                    Run: {entry.run_id}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--color-error)",
                      marginTop: 4,
                    }}
                  >
                    {entry.failure_stage}: {entry.last_error}
                  </div>
                </div>
                <button
                  className="btn-ghost"
                  onClick={() => handleResolve(entry.id)}
                  disabled={resolving[entry.id]}
                  style={{ fontSize: 13, whiteSpace: "nowrap" }}
                >
                  {resolving[entry.id] ? "Resolving..." : "Mark Resolved"}
                </button>
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 20,
                  fontSize: 12,
                  color: "var(--color-text-muted)",
                }}
              >
                <span>Retries: {entry.retry_count}</span>
                <span>Stage: {entry.failure_stage}</span>
                <span>Created: {new Date(entry.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}