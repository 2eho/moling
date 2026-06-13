import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0d0f1a 0%, #141627 50%, #1a1d2e 100%)",
      }}
    >
      {children}
    </div>
  );
}
