import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getWorkflow,
  getWorkflowVersions,
  createVersion,
  validateYaml,
  activateWorkflow,
  deactivateWorkflow,
} from "../api/workflows";
import { getRuns, triggerRun } from "../api/runs";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";

export default function WorkflowDetailPage() {
  const { workflowId } = useParams();
  const [workflow, setWorkflow] = useState(null);
  const [versions, setVersions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  const [yaml, setYaml] = useState("");
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  const [triggering, setTriggering] = useState(false);
  const [triggerPayload, setTriggerPayload] = useState(
    '{"subject": "Test message", "body": "Hello from StackBridge"}'
  );
  const [triggerResult, setTriggerResult] = useState(null);

  useEffect(() => {
    Promise.all([
      getWorkflow(workflowId),
      getWorkflowVersions(workflowId),
      getRuns(workflowId),
    ])
      .then(([wf, v, r]) => {
        setWorkflow(wf);
        setVersions(v);
        setRuns(r.slice(0, 5));
        // Set yaml from current version
        if (v.length > 0) {
          setYaml(v[0].yaml_source);
        }
      })
      .finally(() => setLoading(false));
  }, [workflowId]);

  async function handleValidate() {
    setValidating(true);
    setValidationResult(null);
    try {
      const result = await validateYaml(yaml);
      setValidationResult(result);
    } catch (e) {
      setValidationResult({ valid: false, errors: [e.message] });
    } finally {
      setValidating(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveMsg("");
    try {
      await createVersion(workflowId, yaml);
      const [wf, v] = await Promise.all([
        getWorkflow(workflowId),
        getWorkflowVersions(workflowId),
      ]);
      setWorkflow(wf);
      setVersions(v);
      setSaveMsg("Version saved successfully.");
    } catch (e) {
      setSaveMsg(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleActive() {
    try {
      if (workflow.is_active) {
        await deactivateWorkflow(workflowId);
      } else {
        await activateWorkflow(workflowId);
      }
      const wf = await getWorkflow(workflowId);
      setWorkflow(wf);
    } catch (e) {
      alert(e.message);
    }
  }

  async function handleTrigger(dryRun) {
    setTriggering(true);
    setTriggerResult(null);
    try {
      let payload;
      try {
        payload = JSON.parse(triggerPayload);
      } catch {
        alert("Trigger payload is not valid JSON");
        return;
      }
      const run = await triggerRun(workflowId, payload, dryRun);
      setTriggerResult(run);
      const r = await getRuns(workflowId);
      setRuns(r.slice(0, 5));
    } catch (e) {
      setTriggerResult({ error: e.message });
    } finally {
      setTriggering(false);
    }
  }

  if (loading)
    return (
      <div className="page" style={{ textAlign: "center", paddingTop: 80 }}>
        <LoadingSpinner size={32} />
      </div>
    );

  if (!workflow)
    return (
      <div className="page">
        <p className="error-text">Workflow not found.</p>
      </div>
    );

  return (
    <div className="page">
      <div style={{ marginBottom: 20 }}>
        <Link to="/workflows" style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
          ← Workflows
        </Link>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 28,
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 22,
            fontWeight: 700,
            flex: 1,
          }}
        >
          {workflow.name}
        </h1>
        <StatusBadge status={workflow.is_active ? "active" : "inactive"} />
        <button
          className={workflow.is_active ? "btn-ghost" : "btn-primary"}
          onClick={handleToggleActive}
          style={{ padding: "6px 14px" }}
        >
          {workflow.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>

      <div className="grid-2" style={{ gap: 24 }}>
        {/* Left: Editor */}
        <div>
          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <h2 style={{ fontSize: 15, fontWeight: 600 }}>YAML Editor</h2>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--color-text-muted)",
                }}
              >
                v{workflow.current_version}
              </span>
            </div>
            <textarea
              value={yaml}
              onChange={(e) => {
                setYaml(e.target.value);
                setValidationResult(null);
              }}
              onBlur={handleValidate}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                minHeight: 280,
                lineHeight: 1.6,
              }}
            />

            {validating && (
              <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 6 }}>
                Validating...
              </p>
            )}

            {validationResult && (
              <div
                style={{
                  marginTop: 8,
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  background: validationResult.valid ? "#14532d22" : "#450a0a22",
                  border: `1px solid ${
                    validationResult.valid
                      ? "var(--color-success)"
                      : "var(--color-error)"
                  }`,
                  fontSize: 12,
                  color: validationResult.valid
                    ? "var(--color-success)"
                    : "var(--color-error)",
                }}
              >
                {validationResult.valid
                  ? "✓ Valid YAML"
                  : `✗ ${validationResult.errors?.[0] || "Invalid"}`}
              </div>
            )}

            {saveMsg && (
              <p
                style={{
                  fontSize: 12,
                  marginTop: 6,
                  color: saveMsg.startsWith("Error")
                    ? "var(--color-error)"
                    : "var(--color-success)",
                }}
              >
                {saveMsg}
              </p>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                className="btn-ghost"
                onClick={handleValidate}
                disabled={validating}
                style={{ fontSize: 13 }}
              >
                Validate
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={saving}
                style={{ fontSize: 13 }}
              >
                {saving ? "Saving..." : "Save as New Version"}
              </button>
            </div>
          </div>

          {/* Version History */}
          <div className="card" style={{ marginTop: 16 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
              Version History
            </h2>
            {versions.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
                No versions yet.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {versions.map((v) => (
                  <div
                    key={v.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--color-surface-2)",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
                      v{v.version_number}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                    <button
                      className="btn-ghost"
                      style={{ fontSize: 11, padding: "2px 8px" }}
                      onClick={() => setYaml(v.yaml_source)}
                    >
                      Load
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Trigger + Recent Runs */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
              Manual Trigger
            </h2>
            <label>Payload (JSON)</label>
            <textarea
              value={triggerPayload}
              onChange={(e) => setTriggerPayload(e.target.value)}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                minHeight: 100,
              }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                className="btn-primary"
                onClick={() => handleTrigger(false)}
                disabled={triggering}
                style={{ fontSize: 13 }}
              >
                {triggering ? "Running..." : "Run"}
              </button>
              <button
                className="btn-ghost"
                onClick={() => handleTrigger(true)}
                disabled={triggering}
                style={{ fontSize: 13 }}
              >
                Dry Run
              </button>
            </div>

            {triggerResult && (
              <div style={{ marginTop: 12 }}>
                {triggerResult.error ? (
                  <p className="error-text">{triggerResult.error}</p>
                ) : (
                  <div
                    style={{
                      padding: "8px 12px",
                      background: "var(--color-surface-2)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 12,
                    }}
                  >
                    Run{" "}
                    <Link to={`/runs/${triggerResult.id}`}>
                      {triggerResult.id?.slice(0, 8)}...
                    </Link>{" "}
                    — <StatusBadge status={triggerResult.status} />
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card">
            <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>
              Recent Runs
            </h2>
            {runs.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
                No runs yet.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {runs.map((run) => (
                  <Link
                    key={run.id}
                    to={`/runs/${run.id}`}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 12px",
                      background: "var(--color-surface-2)",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                      textDecoration: "none",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {run.id.slice(0, 8)}...
                    </span>
                    <span
                      style={{ fontSize: 12, color: "var(--color-warning)" }}
                    >
                      ${Number(run.total_cost_usd).toFixed(5)}
                    </span>
                    <StatusBadge status={run.status} />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}