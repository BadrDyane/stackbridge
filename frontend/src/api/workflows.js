import { api } from "./client";

export const getWorkflows = () => api.get("/workflows");
export const getWorkflow = (id) => api.get(`/workflows/${id}`);
export const getWorkflowVersions = (id) => api.get(`/workflows/${id}/versions`);
export const createWorkflow = (yaml) =>
  api.postRaw("/workflows", yaml, "application/x-yaml");
export const createVersion = (id, yaml) =>
  api.postRaw(`/workflows/${id}/versions`, yaml, "application/x-yaml");
export const validateYaml = (yaml) =>
  api.postRaw("/workflows/validate", yaml, "application/x-yaml");
export const activateWorkflow = (id) =>
  api.post(`/workflows/${id}/activate`, {});
export const deactivateWorkflow = (id) =>
  api.post(`/workflows/${id}/deactivate`, {});
export const upsertTriggerConfig = (id, body) =>
  api.patch(`/workflows/${id}/trigger-config`, body);
export const upsertActionConfig = (id, body) =>
  api.patch(`/workflows/${id}/action-config`, body);