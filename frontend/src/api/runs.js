import { api } from "./client";

export const getRuns = (workflowId) =>
  api.get(`/runs${workflowId ? `?workflow_id=${workflowId}` : ""}`);
export const getRun = (id) => api.get(`/runs/${id}`);
export const triggerRun = (workflowId, payload, dryRun = false) =>
  api.post("/runs/trigger", {
    workflow_id: workflowId,
    payload,
    dry_run: dryRun,
  });