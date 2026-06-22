import { Routes, Route, Navigate } from "react-router-dom";
import { AuthGuard } from "./AuthGuard";
import { GlobalErrorBoundary } from "@/components/GlobalErrorBoundary";
import { ToastContainer } from "@/components/ToastContainer";
import { ThemeInitializer } from "@/components/vibe/ThemeInitializer";
import { LandingPage } from "./pages/LandingPage";
import { AuthPage } from "./pages/AuthPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { NewProjectPage } from "./pages/NewProjectPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { HealthPage } from "./pages/HealthPage";
import { Phase4TasksPage } from "./pages/Phase4TasksPage";
import { VaultPage } from "./pages/VaultPage";

export function App() {
  return (
    <>
      <ThemeInitializer />
      <GlobalErrorBoundary>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route
            path="/projects"
            element={
              <AuthGuard>
                <ProjectsPage />
              </AuthGuard>
            }
          />
          <Route
            path="/projects/new"
            element={
              <AuthGuard>
                <NewProjectPage />
              </AuthGuard>
            }
          />
          <Route
            path="/settings"
            element={
              <AuthGuard>
                <SettingsPage />
              </AuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId"
            element={
              <AuthGuard>
                <WorkspacePage />
              </AuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId/health"
            element={
              <AuthGuard>
                <HealthPage />
              </AuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId/phase4/tasks"
            element={
              <AuthGuard>
                <Phase4TasksPage />
              </AuthGuard>
            }
          />
          <Route
            path="/vaults/:projectId"
            element={
              <AuthGuard>
                <VaultPage />
              </AuthGuard>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </GlobalErrorBoundary>
      <ToastContainer />
    </>
  );
}
