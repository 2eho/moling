"use client";

import { Navbar } from "@/components/layout/Navbar";
import { ProjectProvider } from "@/contexts/ProjectContext";
import type { ReactNode } from "react";

export default function ProjectsLayout({ children }: { children: ReactNode }) {
  return (
    <ProjectProvider>
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <Navbar />
        <main style={{ flex: 1, padding: "var(--spacing-6)" }}>{children}</main>
      </div>
    </ProjectProvider>
  );
}
