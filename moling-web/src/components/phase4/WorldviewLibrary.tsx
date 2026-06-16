"use client";

import { useState, useEffect, useCallback } from "react";
import { vaultApi } from "@/lib/api";
import type { VaultWorld, VaultWorldFaction } from "@/lib/types";
import styles from "./WorldviewLibrary.module.css";

interface WorldviewLibraryProps {
  projectId: string;
}

export function WorldviewLibrary({ projectId }: WorldviewLibraryProps) {
  const [worlds, setWorlds] = useState<VaultWorld[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    name: "",
    category: "",
    description: "",
    rules: [] as string[],
    factions: [] as VaultWorldFaction[],
    related_entities: [] as string[],
    source_chapter: undefined as number | undefined,
  });

  const loadWorlds = useCallback(async () => {
    try {
      setLoading(true);
      const res = await vaultApi.getWorld(projectId);
      setWorlds(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载世界观失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadWorlds();
    }
  }, [projectId, loadWorlds]);

  const handleCreate = async () => {
    try {
      await vaultApi.createWorldEntry(projectId, formData);
      setShowCreateForm(false);
      resetForm();
      loadWorlds();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建世界观条目失败");
    }
  };

  const handleUpdate = async (worldId: string) => {
    try {
      await vaultApi.updateWorldEntry(projectId, worldId, formData);
      setEditingId(null);
      resetForm();
      loadWorlds();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新世界观条目失败");
    }
  };

  const handleDelete = async (worldId: string) => {
    if (!confirm("确定要删除这个世界观条目吗？")) return;
    try {
      await vaultApi.deleteWorldEntry(projectId, worldId);
      loadWorlds();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除世界观条目失败");
    }
  };

  const startEdit = (world: VaultWorld) => {
    setEditingId(world.id);
    setFormData({
      name: world.name,
      category: world.category,
      description: world.description,
      rules: world.rules || [],
      factions: world.factions || [],
      related_entities: world.related_entities || [],
      source_chapter: world.source_chapter,
    });
  };

  const resetForm = () => {
    setFormData({
      name: "",
      category: "",
      description: "",
      rules: [],
      factions: [],
      related_entities: [],
      source_chapter: undefined,
    });
  };

  const handleRuleAdd = (rule: string) => {
    if (rule && !formData.rules.includes(rule)) {
      setFormData({ ...formData, rules: [...formData.rules, rule] });
    }
  };

  const handleRuleRemove = (rule: string) => {
    setFormData({
      ...formData,
      rules: formData.rules.filter((r) => r !== rule),
    });
  };

  const addFaction = () => {
    setFormData({
      ...formData,
      factions: [
        ...formData.factions,
        { name: "", description: "", influence: 0 },
      ],
    });
  };

  const updateFaction = (index: number, field: string, value: string | number) => {
    const newFactions = [...formData.factions];
    newFactions[index] = { ...newFactions[index], [field]: value };
    setFormData({ ...formData, factions: newFactions });
  };

  const removeFaction = (index: number) => {
    setFormData({
      ...formData,
      factions: formData.factions.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>世界观库</h3>
        <button
          className={styles.createButton}
          onClick={() => setShowCreateForm(true)}
        >
          + 新增条目
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {showCreateForm && (
        <WorldviewForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreateForm(false);
            resetForm();
          }}
          onRuleAdd={handleRuleAdd}
          onRuleRemove={handleRuleRemove}
          onAddFaction={addFaction}
          onUpdateFaction={updateFaction}
          onRemoveFaction={removeFaction}
          submitLabel="创建"
        />
      )}

      {editingId && (
        <WorldviewForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={() => handleUpdate(editingId)}
          onCancel={() => {
            setEditingId(null);
            resetForm();
          }}
          onRuleAdd={handleRuleAdd}
          onRuleRemove={handleRuleRemove}
          onAddFaction={addFaction}
          onUpdateFaction={updateFaction}
          onRemoveFaction={removeFaction}
          submitLabel="更新"
        />
      )}

      <div className={styles.list}>
        {worlds.length === 0 ? (
          <div className={styles.empty}>暂无世界观数据</div>
        ) : (
          worlds.map((world) => (
            <div key={world.id} className={styles.item}>
              <div className={styles.itemHeader}>
                <div className={styles.worldInfo}>
                  <h5 className={styles.worldName}>{world.name}</h5>
                  <span className={styles.category}>{world.category}</span>
                </div>
                <div className={styles.itemActions}>
                  <button
                    className={styles.editButton}
                    onClick={() => startEdit(world)}
                  >
                    编辑
                  </button>
                  <button
                    className={styles.deleteButton}
                    onClick={() => handleDelete(world.id)}
                  >
                    删除
                  </button>
                </div>
              </div>

              <p className={styles.desc}>{world.description}</p>

              {world.rules && world.rules.length > 0 && (
                <div className={styles.section}>
                  <span className={styles.sectionLabel}>规则</span>
                  <ul className={styles.ruleList}>
                    {world.rules.map((rule, idx) => (
                      <li key={`${rule}-${idx}`} className={styles.rule}>
                        {rule}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {world.factions && world.factions.length > 0 && (
                <div className={styles.section}>
                  <span className={styles.sectionLabel}>势力</span>
                  {world.factions.map((f, idx) => (
                    <div key={f.name || `faction-${idx}`} className={styles.faction}>
                      <div className={styles.factionHeader}>
                        <span className={styles.factionName}>{f.name}</span>
                        <span className={styles.factionInfluence}>
                          影响力: {f.influence}
                        </span>
                      </div>
                      <p className={styles.factionDesc}>{f.description}</p>
                    </div>
                  ))}
                </div>
              )}

              {world.source_chapter && (
                <span className={styles.sourceChapter}>
                  来源: 第{world.source_chapter}章
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// 世界观表单组件
interface WorldviewFormProps {
  formData: {
    name: string;
    category: string;
    description: string;
    rules: string[];
    factions: VaultWorldFaction[];
    related_entities: string[];
    source_chapter: number | undefined;
  };
  setFormData: (data: WorldviewFormProps["formData"]) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onRuleAdd: (rule: string) => void;
  onRuleRemove: (rule: string) => void;
  onAddFaction: () => void;
  onUpdateFaction: (index: number, field: string, value: string | number) => void;
  onRemoveFaction: (index: number) => void;
  submitLabel: string;
}

function WorldviewForm({
  formData,
  setFormData,
  onSubmit,
  onCancel,
  onRuleAdd,
  onRuleRemove,
  onAddFaction,
  onUpdateFaction,
  onRemoveFaction,
  submitLabel,
}: WorldviewFormProps) {
  const [ruleInput, setRuleInput] = useState("");

  return (
    <div className={styles.formOverlay}>
      <div className={styles.form}>
        <h4>{submitLabel}世界观条目</h4>

        <label className={styles.label}>
          名称
          <input
            type="text"
            value={formData.name}
            onChange={(e) =>
              setFormData({ ...formData, name: e.target.value })
            }
            className={styles.input}
          />
        </label>

        <label className={styles.label}>
          分类
          <input
            type="text"
            value={formData.category}
            onChange={(e) =>
              setFormData({ ...formData, category: e.target.value })
            }
            className={styles.input}
            placeholder="如：地理、魔法、科技、历史"
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
          规则
          <div className={styles.ruleInput}>
            <input
              type="text"
              value={ruleInput}
              onChange={(e) => setRuleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onRuleAdd(ruleInput);
                  setRuleInput("");
                }
              }}
              className={styles.input}
              placeholder="输入后按回车添加"
            />
          </div>
          <div className={styles.rules}>
            {formData.rules.map((rule) => (
              <span
                key={rule}
                className={styles.ruleTag}
                onClick={() => onRuleRemove(rule)}
              >
                {rule} ×
              </span>
            ))}
          </div>
        </label>

        <div className={styles.factionsSection}>
          <div className={styles.factionsHeader}>
            <span className={styles.sectionLabel}>势力</span>
            <button className={styles.addFactionButton} onClick={onAddFaction}>
              + 添加势力
            </button>
          </div>

          {formData.factions.map((faction, idx) => (
            <div key={idx} className={styles.factionForm}>
              <input
                type="text"
                placeholder="势力名称"
                value={faction.name}
                onChange={(e) => onUpdateFaction(idx, "name", e.target.value)}
                className={styles.factionInput}
              />
              <input
                type="text"
                placeholder="描述"
                value={faction.description}
                onChange={(e) => onUpdateFaction(idx, "description", e.target.value)}
                className={styles.factionInput}
              />
              <input
                type="number"
                placeholder="影响力"
                value={faction.influence}
                onChange={(e) =>
                  onUpdateFaction(idx, "influence", parseInt(e.target.value) || 0)
                }
                className={styles.factionInput}
              />
              <button
                className={styles.removeFactionButton}
                onClick={() => onRemoveFaction(idx)}
              >
                ×
              </button>
            </div>
          ))}
        </div>

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
