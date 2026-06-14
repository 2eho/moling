"use client";

import { usePathname } from "next/navigation";
import { Navbar } from "./Navbar";
import styles from "./AppShell.module.css";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isSimplePage =
    pathname === "/" ||
    pathname?.startsWith("/landing") ||
    pathname?.startsWith("/auth");

  if (isSimplePage) return <>{children}</>;

  return (
    <div className={styles.shell}>
      <Navbar />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
