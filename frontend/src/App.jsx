import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { isLoggedIn } from "./api/auth";
import Navbar from "./components/Navbar";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import WorkflowsPage from "./pages/WorkflowsPage";
import WorkflowDetailPage from "./pages/WorkflowDetailPage";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import IntegrationsPage from "./pages/IntegrationsPage";
import CostDashboardPage from "./pages/CostDashboardPage";
import DLQPage from "./pages/DLQPage";

function ProtectedLayout({ children }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  return (
    <>
      <Navbar />
      {children}
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedLayout>
              <DashboardPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/workflows"
          element={
            <ProtectedLayout>
              <WorkflowsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/workflows/:workflowId"
          element={
            <ProtectedLayout>
              <WorkflowDetailPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/runs"
          element={
            <ProtectedLayout>
              <RunsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/runs/:runId"
          element={
            <ProtectedLayout>
              <RunDetailPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/integrations"
          element={
            <ProtectedLayout>
              <IntegrationsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/cost"
          element={
            <ProtectedLayout>
              <CostDashboardPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/dlq"
          element={
            <ProtectedLayout>
              <DLQPage />
            </ProtectedLayout>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}