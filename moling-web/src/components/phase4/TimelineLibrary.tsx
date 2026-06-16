"use client";

import { useState, useEffect, useCallback } from "react";
import { vaultApi } from "@/lib/api";
import type { VaultTimeline, VaultTimelineEvent } from "@/lib/types";
import styles from "./TimelineLibrary.module.css";

interface TimelineLibraryProps {
  projectId: string;
}

export function TimelineLibrary({ projectId }: TimelineLibraryProps) {
  const [timelines, setTimelines] = useState<VaultTimeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    day: undefined as number | undefined,
    events: [] as VaultTimelineEvent[],
    precedes: "",
    source_chapter: undefined as number | undefined,
  });

  const loadTimelines = useCallback(async () => {
    try {
      setLoading(true);
      const res = await vaultApi.getTimeline(projectId);
      setTimelines(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载时间线失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadTimelines();
    }
  }, [projectId, loadTimelines]);

  const handleCreate = async () => {
    try {
      await vaultApi.createTimelineEvent(projectId, formData);
      setShowCreateForm(false);
      resetForm();
      loadTimelines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建时间线事件失败");
    }
  };

  const handleUpdate = async (timelineId: string) => {
    try {
      await vaultApi.updateTimelineEvent(projectId, timelineId, formData);
      setEditingId(null);
      resetForm();
      loadTimelines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新时间线事件失败");
    }
  };

  const handleDelete = async (timelineId: string) => {
    if (!confirm("确定要删除这个时间线事件吗？")) return;
    try {
      await vaultApi.deleteTimelineEvent(projectId, timelineId);
      loadTimelines();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除时间线事件失败");
    }
  };

  const startEdit = (timeline: VaultTimeline) => {
    setEditingId(timeline.id);
    setFormData({
      title: timeline.title || "",
      description: timeline.description || "",
      day: timeline.day,
      events: timeline.events || [],
      precedes: timeline.precedes || "",
      source_chapter: timeline.source_chapter,
    });
  };

  const resetForm = () => {
    setFormData({
      title: "",
      description: "",
      day: undefined,
      events: [],
      precedes: "",
      source_chapter: undefined,
    });
  };

  const addEvent = () => {
    setFormData({
      ...formData,
      events: [
        ...formData.events,
        { chapter_number: 0, event: "", importance: 1 },
      ],
    });
  };

  const updateEvent = (index: number, field: string, value: string | number) => {
    const newEvents = [...formData.events];
    newEvents[index] = { ...newEvents[index], [field]: value };
    setFormData({ ...formData, events: newEvents });
  };

  const removeEvent = (index: number) => {
    setFormData({
      ...formData,
      events: formData.events.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>时间线库</h3>
        <button
          className={styles.createButton}
          onClick={() => setShowCreateForm(true)}
        >
          + 新增事件
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {showCreateForm && (
        <TimelineForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreateForm(false);
            resetForm();
          }}
          onAddEvent={addEvent}
          onUpdateEvent={updateEvent}
          onRemoveEvent={removeEvent}
          submitLabel="创建"
        />
      )}

      {editingId && (
        <TimelineForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={() => handleUpdate(editingId)}
          onCancel={() => {
            setEditingId(null);
            resetForm();
          }}
          onAddEvent={addEvent}
          onUpdateEvent={updateEvent}
          onRemoveEvent={removeEvent}
          submitLabel="更新"
        />
      )}

      <div className={styles.list}>
        {timelines.length === 0 ? (
          <div className={styles.empty}>暂无时间线数据</div>
        ) : (
          timelines.map((timeline) => (
            <div key={timeline.id} className={styles.item}>
              <div className={styles.itemHeader}>
                <div className={styles.timelineInfo}>
                  <h5 className={styles.timelineTitle}>
                    {timeline.title || "未命名事件"}
                  </h5>
                  {timeline.description && (
                    <p className={styles.timelineDesc}>{timeline.description}</p>
                  )}
                  {timeline.day !== undefined && (
                    <span className={styles.dayBadge}>第 {timeline.day} 天</span>
                  )}
                </div>
                <div className={styles.itemActions}>
                  <button
                    className={styles.editButton}
                    onClick={() => startEdit(timeline)}
                  >
                    编辑
                  </button>
                  <button
                    className={styles.deleteButton}
                    onClick={() => handleDelete(timeline.id)}
                  >
                    删除
                  </button>
                </div>
              </div>

              {timeline.events && timeline.events.length > 0 && (
                <div className={styles.events}>
                  {timeline.events.map((event, idx) => (
                    <div key={idx} className={styles.event}>
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
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// 时间线表单组件
interface TimelineFormProps {
  formData: {
    title: string;
    description: string;
    day: number | undefined;
    events: VaultTimelineEvent[];
    precedes: string;
    source_chapter: number | undefined;
  };
  setFormData: (data: TimelineFormProps["formData"]) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onAddEvent: () => void;
  onUpdateEvent: (index: number, field: string, value: string | number) => void;
  onRemoveEvent: (index: number) => void;
  submitLabel: string;
}

function TimelineForm({
  formData,
  setFormData,
  onSubmit,
  onCancel,
  onAddEvent,
  onUpdateEvent,
  onRemoveEvent,
  submitLabel,
}: TimelineFormProps) {
  return (
    <div className={styles.formOverlay}>
      <div className={styles.form}>
        <h4>{submitLabel}时间线事件</h4>

        <label className={styles.label}>
          标题
          <input
            type="text"
            value={formData.title}
            onChange={(e) =>
              setFormData({ ...formData, title: e.target.value })
            }
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          描述
          <textarea
            value={formData.description}
            onChange={(e) =>
              setFormData({ ...formData, description: e.target.value })
            }
            className={styles.textarea}
            rows={3}
          />
        </label>

        <label className={styles.label}>
          天数
          <input
            type="number"
            value={formData.day || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                day: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          来源章节
          <input
            type="number"
            value={formData.source_chapter || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                source_chapter: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            className={styles.input}
          />
        </label>

        <div className={styles.eventsSection}>
          <div className={styles.eventsHeader}>
            <span className={styles.sectionLabel}>事件列表</span>
            <button className={styles.addEventButton} onClick={onAddEvent}>
              + 添加事件
            </button>
          </div>

          {formData.events.map((event, idx) => (
            <div key={idx} className={styles.eventForm}>
              <input
                type="number"
                placeholder="章节号"
                value={event.chapter_number || ""}
                onChange={(e) =>
                  onUpdateEvent(
                    idx,
                    "chapter_number",
                    e.target.value ? parseInt(e.target.value) : 0
                  )
                }
                className={styles.eventInput}
              />
              <input
                type="text"
                placeholder="事件描述"
                value={event.event}
                onChange={(e) => onUpdateEvent(idx, "event", e.target.value)}
                className={styles.eventInput}
              />
              <input
                type="number"
                placeholder="重要性(1-5)"
                value={event.importance}
                min={1}
                max={5}
                onChange={(e) =>
                  onUpdateEvent(
                    idx,
                    "importance",
                    e.target.value ? parseInt(e.target.value) : 1
                  )
                }
                className={styles.eventInput}
              />
              <button
                className={styles.removeEventButton}
                onClick={() => onRemoveEvent(idx)}
              >
                ×
              </button>
            </div>
          ))}
        </div>

        <div className={styles.formActions}>
          <button className={styles.cancelButton} onClick={onCancel}>
            取消
          </button>
          <button className={styles.submitButton} onClick={onSubmit}>
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
