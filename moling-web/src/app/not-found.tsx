"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import styles from "./not-found.module.css";

export default function NotFound() {
  const router = useRouter();

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 20h9"/>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>
        <div className={styles.code}>404</div>
        <h1 className={styles.title}>这章还没写</h1>
        <p className={styles.desc}>
          你找的页面不在墨灵的世界观里。
          <br />
          可能是链接错了，或者它还在构思中。
        </p>
        <Button onClick={() => router.push("/projects")}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{marginRight:"6px", verticalAlign:"middle"}}>
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          回我的作品
        </Button>
        <div className={styles.links}>
          <button className={styles.linkBtn} onClick={() => router.push("/")}>首页</button>
          <button className={styles.linkBtn} onClick={() => router.push("/auth")}>登录</button>
        </div>
      </div>
    </div>
  );
}
