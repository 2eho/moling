"use client";

import { useState, useEffect, useCallback } from "react";
import { vaultApi } from "@/lib/api";
import type { VaultPlotPromise } from "@/lib/types";
import styles from "./ForeshadowingLibrary.module.css";

interface ForeshadowingLibraryProps {
  projectId: string;
}

const statusLabels: Record<string, string> = {
  pending: "待兑现",
  fulfilled: "已兑现",
  broken: "已破裂",
};

const statusColors: Record<string, string> = {
  pending: "var(--color-warning)",
  fulfilled: "var(--color-success)",
  broken: "var(--color-danger)",
};

export function ForeshadowingLibrary({
  projectId,
}: ForeshadowingLibraryProps) {
  const [promises, setPromises] = useState<VaultPlotPromise[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    description: "",
    status: "pending" as "pending" | "fulfilled" | "broken",
    introduced_at: 1,
    resolved_at: undefined as number | undefined,
    type: "",
    urgency: "",
    title: "",
    redeem_window: undefined as number | undefined,
  });

  const loadPromises = useCallback(async () => {
    try {
      setLoading(true);
      const res = await vaultApi.getPlotPromises(projectId);
      setPromises(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载伏笔失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadPromises();
    }
  }, [projectId, loadPromises]);

  const handleCreate = async () => {
    try {
      await vaultApi.createPlotPromise(projectId, formData);
      setShowCreateForm(false);
      resetForm();
      loadPromises();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建伏笔失败");
    }
  };

  const handleUpdate = async (promiseId: string) => {
    try {
      await vaultApi.updatePlotPromise(projectId, promiseId, formData);
      setEditingId(null);
      resetForm();
      loadPromises();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新伏笔失败");
    }
  };

  const handleDelete = async (promiseId: string) => {
    if (!confirm("确定要删除这个伏笔吗？")) return;
    try {
      await vaultApi.deletePlotPromise(projectId, promiseId);
      loadPromises();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除伏笔失败");
    }
  };

  const startEdit = (pp: VaultPlotPromise) => {
    setEditingId(pp.id);
    setFormData({
      description: pp.description,
      status: pp.status,
      introduced_at: pp.introduced_at,
      resolved_at: pp.resolved_at,
      type: pp.type || "",
      urgency: pp.urgency || "",
      title: pp.title || "",
      redeem_window: pp.redeem_window,
    });
  };

  const resetForm = () => {
    setFormData({
      description: "",
      status: "pending",
      introduced_at: 1,
      resolved_at: undefined,
      type: "",
      urgency: "",
      title: "",
      redeem_window: undefined,
    });
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>伏笔库</h3>
        <button
          className={styles.createButton}
          onClick={() => setShowCreateForm(true)}
        >
          + 新增伏笔
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {showCreateForm && (
        <ForeshadowingForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreateForm(false);
            resetForm();
          }}
          submitLabel="创建"
        />
      )}

      {editingId && (
        <ForeshadowingForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={() => handleUpdate(editingId)}
          onCancel={() => {
            setEditingId(null);
            resetForm();
          }}
          submitLabel="更新"
        />
      )}

      <div className={styles.list}>
        {promises.length === 0 ? (
          <div className={styles.empty}>暂无伏笔数据</div>
        ) : (
          promises.map((pp) => (
            <div key={pp.id} className={styles.item}>
              <div className={styles.itemHeader}>
                <span
                  className={styles.status}
                  style={{
                    backgroundColor:
                      statusColors[pp.status] ?? "var(--color-text-disabled)",
                  }}
                >
                  {statusLabels[pp.status] ?? pp.status}
                </span>
                <span className={styles.chapter}>
                  第{pp.introduced_at}章引入
                </span>
              </div>

              {pp.title && (
                <h5 className={styles.itemTitle}>{pp.title}</h5>
              )}

              <p className={styles.description}>{pp.description}</p>

              {pp.type && (
                <span className={styles.meta}>类型: {pp.type}</span>
              )}

              {pp.urgency && (
                <span className={styles.meta}>紧急度: {pp.urgency}</span>
              )}

              {pp.resolved_at && (
                <span className={styles.resolved}>
                  已解决于第{pp.resolved_at}章
                </span>
              )}

              <div className={styles.actions}>
                <button
                  className={styles.editButton}
                  onClick={() => startEdit(pp)}
                >
                  编辑
                </button>
                <button
                  className={styles.deleteButton}
                  onClick={() => handleDelete(pp.id)}
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// 伏笔表单组件
interface ForeshadowingFormProps {
  formData: {
    description: string;
    status: "pending" | "fulfilled" | "broken";
    introduced_at: number;
    resolved_at: number | undefined;
    type: string;
    urgency: string;
    title: string;
    redeem_window: number | undefined;
  };
  setFormData: (data: ForeshadowingFormProps["formData"]) => void;
  onSubmit: () => void;
  onCancel: () => void;
  submitLabel: string;
}

function ForeshadowingForm({
  formData,
  setFormData,
  onSubmit,
  onCancel,
  submitLabel,
}: ForeshadowingFormProps) {
  return (
    <div className={styles.formOverlay}>
      <div className={styles.form}>
        <h4>{submitLabel}伏笔</h4>

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
          状态
          <select
            value={formData.status}
            onChange={(e) =>
              setFormData({
                ...formData,
                status: e.target.value as "pending" | "fulfilled" | "broken",
              })
            }
            className={styles.select}
          >
            <option value="pending">待兑现</option>
            <option value="fulfilled">已兑现</option>
            <option value="broken">已破裂</option>
          </select>
        </label>

        <label className={styles.label}>
          引入章节
          <input
            type="number"
            value={formData.introduced_at}
            min={1}
            onChange={(e) =>
              setFormData({
                ...formData,
                introduced_at: e.target.value
                  ? parseInt(e.target.value)
                  : 1,
              })
            }
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          解决章节（可选）
          <input
            type="number"
            value={formData.resolved_at || ""}
            min={1}
            onChange={(e) =>
              setFormData({
                ...formData,
                resolved_at: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          类型
          <input
            type="text"
            value={formData.type}
            onChange={(e) =>
              setFormData({ ...formData, type: e.target.value })
            }
            className={styles.input}
            placeholder="如：悬念、线索、预言"
          />
        </label>

        <label className={styles.label}>
          紧急度
          <input
            type="text"
            value={formData.urgency}
            onChange={(e) =>
              setFormData({ ...formData, urgency: e.target.value })
            }
            className={styles.input}
            placeholder="如：高、中、低"
          />
        </label>

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
