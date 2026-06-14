"use client";

import { AuthProvider } from "@/contexts/AuthContext";
import { SystemHealthProvider } from "@/contexts/SystemHealthContext";
import { SystemHealthBanner } from "@/components/health/SystemHealthBanner";
import { ToastContainer } from "@/components/ui/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <SystemHealthProvider>
        {/* System health banner displayed at the top of every page */}
        <SystemHealthBanner />
        {children}
      </SystemHealthProvider>
      <ToastContainer />
    </AuthProvider>
  );
}
