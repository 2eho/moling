import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { GlobalErrorBoundary } from "@/components/GlobalErrorBoundary";
import { ToastContainer } from "@/components/ToastContainer";
import { ThemeInitializer } from "@/components/vibe/ThemeInitializer";
import { AuthGuard } from "./AuthGuard";

// ── Route-level code splitting ──
// Landing must stay eager — it's the entry point and tiny (< 3KB)
import { LandingPage } from "./pages/LandingPage";

const AuthPage = lazy(() => import("./pages/AuthPage").then((m) => ({ default: m.AuthPage })));
const ProjectsPage = lazy(() =>
  import("./pages/ProjectsPage").then((m) => ({ default: m.ProjectsPage })),
);
const NewProjectPage = lazy(() =>
  import("./pages/NewProjectPage").then((m) => ({ default: m.NewProjectPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);
const WorkspacePage = lazy(() =>
  import("./pages/WorkspacePage").then((m) => ({ default: m.WorkspacePage })),
);
const HealthPage = lazy(() =>
  import("./pages/HealthPage").then((m) => ({ default: m.HealthPage })),
);
const Phase4TasksPage = lazy(() =>
  import("./pages/Phase4TasksPage").then((m) => ({ default: m.Phase4TasksPage })),
);
const VaultPage = lazy(() => import("./pages/VaultPage").then((m) => ({ default: m.VaultPage })));

/** Route-level suspense fallback — subtle spinner, no layout jump */
function RouteFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-th-bg">
      <div className="w-8 h-8 rounded-full border-2 border-th-accent border-t-transparent animate-spin" />
    </div>
  );
}

/**
 * Per-route error boundary — isolates crashes to individual routes.
 * Each route gets its own recovery surface; the outer GlobalErrorBoundary
 * is the last-resort catch-all.
 */
function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  return <GlobalErrorBoundary>{children}</GlobalErrorBoundary>;
}

/** Wrap an auth-protected lazy route with error isolation + suspense */
function LazyAuthGuard({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <RouteErrorBoundary>
        <Suspense fallback={<RouteFallback />}>{children}</Suspense>
      </RouteErrorBoundary>
    </AuthGuard>
  );
}

export function App() {
  return (
    <>
      <ThemeInitializer />
      <GlobalErrorBoundary>
        <Routes>
          {/* Landing — eager, always loaded */}
          <Route
            path="/"
            element={
              <RouteErrorBoundary>
                <LandingPage />
              </RouteErrorBoundary>
            }
          />

          {/* Auth — lazy */}
          <Route
            path="/auth"
            element={
              <RouteErrorBoundary>
                <Suspense fallback={<RouteFallback />}>
                  <AuthPage />
                </Suspense>
              </RouteErrorBoundary>
            }
          />

          {/* Protected routes — lazy + auth guard + per-route error isolation */}
          <Route
            path="/projects"
            element={
              <LazyAuthGuard>
                <ProjectsPage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/projects/new"
            element={
              <LazyAuthGuard>
                <NewProjectPage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/settings"
            element={
              <LazyAuthGuard>
                <SettingsPage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId"
            element={
              <LazyAuthGuard>
                <WorkspacePage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId/health"
            element={
              <LazyAuthGuard>
                <HealthPage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/workspace/:projectId/phase4/tasks"
            element={
              <LazyAuthGuard>
                <Phase4TasksPage />
              </LazyAuthGuard>
            }
          />
          <Route
            path="/vaults/:projectId"
            element={
              <LazyAuthGuard>
                <VaultPage />
              </LazyAuthGuard>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </GlobalErrorBoundary>
      <ToastContainer />
    </>
  );
}
