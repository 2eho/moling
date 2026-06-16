"use client";

import { useState, useEffect, useCallback } from "react";
import { vaultApi } from "@/lib/api";
import type { VaultCharacter, VaultCharacterRelationship } from "@/lib/types";
import styles from "./CharacterLibrary.module.css";

interface CharacterLibraryProps {
  projectId: string;
}

export function CharacterLibrary({ projectId }: CharacterLibraryProps) {
  const [characters, setCharacters] = useState<VaultCharacter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState({
    name: "",
    role: "",
    description: "",
    traits: [] as string[],
    background: "",
    arc: "",
    relationships: [] as VaultCharacterRelationship[],
    location: "",
    appearance: "",
    personality: "",
    knowledge: "",
  });

  const loadCharacters = useCallback(async () => {
    try {
      setLoading(true);
      const res = await vaultApi.getCharacters(projectId);
      setCharacters(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载角色失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadCharacters();
    }
  }, [projectId, loadCharacters]);

  const handleCreate = async () => {
    try {
      await vaultApi.createCharacter(projectId, formData);
      setShowCreateForm(false);
      resetForm();
      loadCharacters();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建角色失败");
    }
  };

  const handleUpdate = async (characterId: string) => {
    try {
      await vaultApi.updateCharacter(projectId, characterId, formData);
      setEditingId(null);
      resetForm();
      loadCharacters();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新角色失败");
    }
  };

  const handleDelete = async (characterId: string) => {
    if (!confirm("确定要删除这个角色吗？")) return;
    try {
      await vaultApi.deleteCharacter(projectId, characterId);
      loadCharacters();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除角色失败");
    }
  };

  const startEdit = (char: VaultCharacter) => {
    setEditingId(char.id);
    setFormData({
      name: char.name,
      role: char.role,
      description: char.description,
      traits: char.traits || [],
      background: char.background || "",
      arc: char.arc || "",
      relationships: char.relationships || [],
      location: char.location || "",
      appearance: char.appearance || "",
      personality: char.personality || "",
      knowledge: char.knowledge || "",
    });
  };

  const resetForm = () => {
    setFormData({
      name: "",
      role: "",
      description: "",
      traits: [],
      background: "",
      arc: "",
      relationships: [],
      location: "",
      appearance: "",
      personality: "",
      knowledge: "",
    });
  };

  const handleTraitAdd = (trait: string) => {
    if (trait && !formData.traits.includes(trait)) {
      setFormData({ ...formData, traits: [...formData.traits, trait] });
    }
  };

  const handleTraitRemove = (trait: string) => {
    setFormData({
      ...formData,
      traits: formData.traits.filter((t) => t !== trait),
    });
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>角色库</h3>
        <button
          className={styles.createButton}
          onClick={() => setShowCreateForm(true)}
        >
          + 新增角色
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {showCreateForm && (
        <CharacterForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowCreateForm(false);
            resetForm();
          }}
          onTraitAdd={handleTraitAdd}
          onTraitRemove={handleTraitRemove}
          submitLabel="创建"
        />
      )}

      {editingId && (
        <CharacterForm
          formData={formData}
          setFormData={setFormData}
          onSubmit={() => handleUpdate(editingId)}
          onCancel={() => {
            setEditingId(null);
            resetForm();
          }}
          onTraitAdd={handleTraitAdd}
          onTraitRemove={handleTraitRemove}
          submitLabel="更新"
        />
      )}

      <div className={styles.list}>
        {characters.length === 0 ? (
          <div className={styles.empty}>暂无角色数据</div>
        ) : (
          characters.map((char) => (
            <div key={char.id} className={styles.item}>
              <button
                className={styles.itemHeader}
                onClick={() =>
                  setExpandedId(expandedId === char.id ? null : char.id)
                }
              >
                <div className={styles.avatar}>{char.name.charAt(0)}</div>
                <div className={styles.info}>
                  <span className={styles.name}>{char.name}</span>
                  <span className={styles.role}>{char.role}</span>
                </div>
                <span className={styles.expandIcon}>
                  {expandedId === char.id ? "▲" : "▼"}
                </span>
              </button>

              {expandedId === char.id && (
                <div className={styles.detail}>
                  <p className={styles.desc}>{char.description}</p>

                  {char.traits && char.traits.length > 0 && (
                    <div className={styles.traits}>
                      {char.traits.map((trait) => (
                        <span key={trait} className={styles.trait}>
                          {trait}
                        </span>
                      ))}
                    </div>
                  )}

                  {char.background && (
                    <div className={styles.section}>
                      <span className={styles.sectionLabel}>背景</span>
                      <p className={styles.sectionText}>{char.background}</p>
                    </div>
                  )}

                  {char.arc && (
                    <div className={styles.section}>
                      <span className={styles.sectionLabel}>成长弧线</span>
                      <p className={styles.sectionText}>{char.arc}</p>
                    </div>
                  )}

                  {char.relationships && char.relationships.length > 0 && (
                    <div className={styles.section}>
                      <span className={styles.sectionLabel}>关系</span>
                      {char.relationships.map((rel, i) => (
                        <p
                          key={rel.character_id || `rel-${i}`}
                          className={styles.sectionText}
                        >
                          {rel.relationship}: {rel.description}
                        </p>
                      ))}
                    </div>
                  )}

                  <div className={styles.actions}>
                    <button
                      className={styles.editButton}
                      onClick={() => startEdit(char)}
                    >
                      编辑
                    </button>
                    <button
                      className={styles.deleteButton}
                      onClick={() => handleDelete(char.id)}
                    >
                      删除
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// 角色表单组件
interface CharacterFormProps {
  formData: {
    name: string;
    role: string;
    description: string;
    traits: string[];
    background: string;
    arc: string;
    relationships: VaultCharacterRelationship[];
    location: string;
    appearance: string;
    personality: string;
    knowledge: string;
  };
  setFormData: (data: CharacterFormProps["formData"]) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onTraitAdd: (trait: string) => void;
  onTraitRemove: (trait: string) => void;
  submitLabel: string;
}

function CharacterForm({
  formData,
  setFormData,
  onSubmit,
  onCancel,
  onTraitAdd,
  onTraitRemove,
  submitLabel,
}: CharacterFormProps) {
  const [traitInput, setTraitInput] = useState("");

  return (
    <div className={styles.formOverlay}>
      <div className={styles.form}>
        <h4>{submitLabel}角色</h4>

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
          角色定位
          <input
            type="text"
            value={formData.role}
            onChange={(e) =>
              setFormData({ ...formData, role: e.target.value })
            }
            className={styles.input}
            placeholder="如：主角、配角、反派"
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
          特征标签
          <div className={styles.traitInput}>
            <input
              type="text"
              value={traitInput}
              onChange={(e) => setTraitInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onTraitAdd(traitInput);
                  setTraitInput("");
                }
              }}
              className={styles.input}
              placeholder="输入后按回车添加"
            />
          </div>
          <div className={styles.traits}>
            {formData.traits.map((trait) => (
              <span
                key={trait}
                className={styles.trait}
                onClick={() => onTraitRemove(trait)}
              >
                {trait} ×
              </span>
            ))}
          </div>
        </label>

        <label className={styles.label}>
          背景故事
          <textarea
            value={formData.background}
            onChange={(e) =>
              setFormData({ ...formData, background: e.target.value })
            }
            className={styles.textarea}
            rows={3}
          />
        </label>

        <label className={styles.label}>
          成长弧线
          <textarea
            value={formData.arc}
            onChange={(e) =>
              setFormData({ ...formData, arc: e.target.value })
            }
            className={styles.textarea}
            rows={2}
          />
        </label>

        <label className={styles.label}>
          位置
          <input
            type="text"
            value={formData.location}
            onChange={(e) =>
              setFormData({ ...formData, location: e.target.value })
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
