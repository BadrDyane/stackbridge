import { api } from "./client";

export const getIntegrations = () => api.get("/integrations");
export const getAuthUrl = (platform) =>
  api.get(`/integrations/${platform}/auth-url`);
export const testIntegration = (id) =>
  api.post(`/integrations/${id}/test`, {});
export const deleteIntegration = (id) => api.delete(`/integrations/${id}`);
export const getDLQ = () => api.get("/dlq");
export const resolveDLQ = (id) => api.post(`/dlq/${id}/resolve`, {});