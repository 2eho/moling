"use client";

import styles from "./TimelineList.module.css";
import type { VaultTimeline } from "@/lib/types";

interface TimelineListProps {
  timelines: VaultTimeline[];
}

export function TimelineList({ timelines }: TimelineListProps) {
  if (timelines.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyText}>暂无时间线数据</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {timelines.map((tl) => (
        <div key={tl.id} className={styles.timeline}>
          <div className={styles.header}>
            <h5 className={styles.title}>{tl.title}</h5>
            {tl.description && (
              <p className={styles.desc}>{tl.description}</p>
            )}
          </div>
          <div className={styles.events}>
            {tl.events.map((event, idx) => (
              <div key={`ch${event.chapter_number}-${idx}`} className={styles.event}>
                <div className={styles.eventDot}>
                  {event.importance >= 4 && (
                    <span className={styles.keyEvent}>★</span>
                  )}
                </div>
                <div className={styles.eventContent}>
                  <span className={styles.chapter}>
                    第{event.chapter_number}章
                  </span>
                  <span className={styles.eventText}>{event.event}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
