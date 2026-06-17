"use client";

import { useEffect } from "react";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { SystemHealthProvider } from "@/contexts/SystemHealthContext";
import { SystemHealthBanner } from "@/components/health/SystemHealthBanner";
import { ToastContainer } from "@/components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  // ✅ DEV MODE: load mock handlers when mock mode is enabled
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_MOCK_ENABLED === "true") {
      import("@/mock").catch(() => {});
    }
  }, []);

  return (
    <AuthProvider>
      <ProjectProvider>
        <SystemHealthProvider>
          {/* System health banner displayed at the top of every page */}
          <SystemHealthBanner />
          {children}
        </SystemHealthProvider>
        <ToastContainer />
      </ProjectProvider>
    </AuthProvider>
  );
}
