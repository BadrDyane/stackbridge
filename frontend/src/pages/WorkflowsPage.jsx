import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getWorkflows, createWorkflow } from "../api/workflows";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";

const DEFAULT_YAML = `name: My New Workflow
description: Describe what this workflow does
trigger:
  type: manual
ai_step:
  task_type: classify_and_summarize
  output_schema:
    priority:
      type: string
      enum: [low, medium, high, urgent]
    summary:
      type: string
action:
  type: slack_post
  integration_id: REPLACE_WITH_INTEGRATION_ID
  config:
    channel: general
    template: "[{priority}]: {summary}"
`;

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [yaml, setYaml] = useState(DEFAULT_YAML);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    getWorkflows().then(setWorkflows).finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    setCreating(true);
    setCreateError("");
    try {
      const wf = await createWorkflow(yaml);
      setWorkflows((prev) => [wf, ...prev]);
      setShowCreate(false);
      setYaml(DEFAULT_YAML);
    } catch (e) {
      setCreateError(e.message);
    } finally {
      setCreating(false);
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          Workflows
        </h1>
        <button className="btn-primary" onClick={() => setShowCreate((s) => !s)}>
          {showCreate ? "Cancel" : "+ New Workflow"}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
            Create Workflow
          </h2>
          <label>YAML Definition</label>
          <textarea
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            style={{ fontFamily: "var(--font-mono)", fontSize: 12, minHeight: 240 }}
          />
          {createError && <p className="error-text">{createError}</p>}
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              className="btn-primary"
              onClick={handleCreate}
              disabled={creating}
            >
              {creating ? "Creating..." : "Create"}
            </button>
            <button className="btn-ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {workflows.length === 0 ? (
        <div className="card empty-state">
          <h3>No workflows yet</h3>
          <p>Create your first workflow above.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {workflows.map((wf) => (
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
                  padding: "16px 20px",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{wf.name}</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                    {wf.description || "No description"} · {wf.trigger_type} · v
                    {wf.current_version}
                  </div>
                </div>
                <StatusBadge status={wf.is_active ? "active" : "inactive"} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}