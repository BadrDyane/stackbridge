import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRun } from "../api/runs";
import StatusBadge from "../components/StatusBadge";
import JsonViewer from "../components/JsonViewer";
import LoadingSpinner from "../components/LoadingSpinner";

function StepCard({ step }) {
  const [open, setOpen] = useState(step.status !== "completed");

  const STEP_LABELS = {
    trigger_normalize: "1. Trigger Normalize",
    ai_process: "2. AI Process",
    action_dispatch: "3. Action Dispatch",
  };

  return (
    <div
      className="card"
      style={{ marginBottom: 12, padding: 0, overflow: "hidden" }}
    >
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "14px 20px",
          cursor: "pointer",
          background: open ? "var(--color-surface-2)" : "transparent",
          borderBottom: open ? "1px solid var(--color-border)" : "none",
        }}
      >
        <span style={{ fontSize: 18 }}>{open ? "▼" : "▶"}</span>
        <span style={{ fontWeight: 600, flex: 1 }}>
          {STEP_LABELS[step.step_type] || step.step_type}
        </span>
        {step.model_used && (
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-text-muted)",
              background: "var(--color-surface)",
              padding: "2px 8px",
              borderRadius: 4,
              border: "1px solid var(--color-border)",
            }}
          >
            {step.model_used}
          </span>
        )}
        {step.prompt_tokens > 0 && (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
            {step.prompt_tokens + step.completion_tokens} tokens · $
            {Number(step.cost_usd).toFixed(6)}
          </span>
        )}
        <StatusBadge status={step.status} />
      </div>

      {open && (
        <div style={{ padding: 20 }}>
          {step.error_details && (
            <div
              style={{
                background: "#450a0a",
                border: "1px solid var(--color-error)",
                borderRadius: "var(--radius-sm)",
                padding: 12,
                color: "var(--color-error)",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                marginBottom: 16,
              }}
            >
              {step.error_details.error}
            </div>
          )}

          <div className="grid-2">
            <div>
              <label style={{ marginBottom: 8, display: "block" }}>Input</label>
              <JsonViewer data={step.input_payload} />
            </div>
            <div>
              <label style={{ marginBottom: 8, display: "block" }}>Output</label>
              <JsonViewer data={step.output_payload} />
            </div>
          </div>

          {step.prompt_tokens > 0 && (
            <div
              style={{
                display: "flex",
                gap: 24,
                marginTop: 16,
                padding: "12px 16px",
                background: "var(--color-surface-2)",
                borderRadius: "var(--radius-sm)",
                fontSize: 13,
              }}
            >
              <span>
                <span style={{ color: "var(--color-text-muted)" }}>Prompt tokens: </span>
                <strong>{step.prompt_tokens}</strong>
              </span>
              <span>
                <span style={{ color: "var(--color-text-muted)" }}>Completion tokens: </span>
                <strong>{step.completion_tokens}</strong>
              </span>
              <span>
                <span style={{ color: "var(--color-text-muted)" }}>Cost: </span>
                <strong style={{ color: "var(--color-warning)" }}>
                  ${Number(step.cost_usd).toFixed(6)}
                </strong>
              </span>
              <span>
                <span style={{ color: "var(--color-text-muted)" }}>Attempts: </span>
                <strong>{step.attempt_count}</strong>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RunDetailPage() {
  const { runId } = useParams();
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getRun(runId)
      .then(setRun)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  if (error)
    return (
      <div className="page">
        <p className="error-text">{error}</p>
      </div>
    );

  return (
    <div className="page">
      <div style={{ marginBottom: 24 }}>
        <Link to="/runs" style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
          ← Back to Runs
        </Link>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div style={{ flex: 1 }}>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 20,
              fontWeight: 700,
              marginBottom: 4,
            }}
          >
            Run Inspector
          </h1>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-text-muted)",
            }}
          >
            {run.id}
          </div>
        </div>
        <StatusBadge status={run.status} />
      </div>

      {/* Run metadata */}
      <div
        className="card"
        style={{
          display: "flex",
          gap: 32,
          marginBottom: 24,
          padding: "16px 20px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Trigger</div>
          <div style={{ fontWeight: 500 }}>{run.trigger_source}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Dry Run</div>
          <div style={{ fontWeight: 500 }}>{run.is_dry_run ? "Yes" : "No"}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Total Tokens</div>
          <div style={{ fontWeight: 500 }}>{run.total_tokens}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Total Cost</div>
          <div style={{ fontWeight: 500, color: "var(--color-warning)" }}>
            ${Number(run.total_cost_usd).toFixed(6)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Version</div>
          <div style={{ fontWeight: 500 }}>v{run.version_number}</div>
        </div>
        {run.error_message && (
          <div>
            <div style={{ fontSize: 12, color: "var(--color-error)" }}>Error</div>
            <div style={{ color: "var(--color-error)", fontSize: 13 }}>
              {run.error_message}
            </div>
          </div>
        )}
      </div>

      {/* Steps */}
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
        Steps ({run.steps?.length || 0})
      </h2>
      {run.steps?.length === 0 ? (
        <div className="empty-state">
          <p>No steps recorded.</p>
        </div>
      ) : (
        run.steps?.map((step) => <StepCard key={step.id} step={step} />)
      )}
    </div>
  );
}