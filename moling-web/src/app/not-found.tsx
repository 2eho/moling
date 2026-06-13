"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import styles from "./not-found.module.css";

export default function NotFound() {
  const router = useRouter();

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        <div className={styles.icon}>🖋️</div>
        <div className={styles.code}>404</div>
        <h1 className={styles.title}>这章还没写</h1>
        <p className={styles.desc}>
          你找的页面不在墨灵的世界观里。
          <br />
          可能是链接错了，或者它还在构思中。
        </p>
        <Button onClick={() => router.push("/")}>← 返回首页</Button>
      </div>
    </div>
  );
}
