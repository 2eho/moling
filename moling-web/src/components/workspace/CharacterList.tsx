"use client";

import { useState } from "react";
import styles from "./CharacterList.module.css";
import type { VaultCharacter } from "@/lib/types";

interface CharacterListProps {
  characters: VaultCharacter[];
}

export function CharacterList({ characters }: CharacterListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (characters.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyText}>暂无角色数据</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {characters.map((char) => (
        <div key={char.id} className={styles.item}>
          <button
            className={styles.header}
            onClick={() =>
              setExpandedId(expandedId === char.id ? null : char.id)
            }
          >
            <div className={styles.avatar}>
              {char.name.charAt(0)}
            </div>
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
              <div className={styles.traits}>
                {char.traits.map((trait) => (
                  <span key={trait} className={styles.trait}>
                    {trait}
                  </span>
                ))}
              </div>
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
              {char.relationships.length > 0 && (
                <div className={styles.section}>
                  <span className={styles.sectionLabel}>关系</span>
                  {char.relationships.map((rel, i) => (
                    <p key={rel.character_id || `rel-${i}`} className={styles.sectionText}>
                      {rel.relationship}: {rel.description}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
