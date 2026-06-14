'use client';

import { useState, useEffect, use } from 'react';
import styles from './Vault.module.css';
import { vaultApi } from '@/lib/api';
import type {
  VaultCharacter,
  VaultTimeline,
  VaultPlotPromise,
  VaultWorld,
} from '@/lib/types';

export default function VaultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: projectId } = use(params);
  const [activeTab, setActiveTab] = useState<'characters' | 'timeline' | 'commitments' | 'worldview'>('characters');

  // 角色库
  const [characters, setCharacters] = useState<VaultCharacter[]>([]);
  const [showCharacterForm, setShowCharacterForm] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<VaultCharacter | null>(null);
  const [characterForm, setCharacterForm] = useState<Partial<VaultCharacter>>({
    name: '',
    role: 'mc',
  });

  // 时间线库
  const [events, setEvents] = useState<VaultTimeline[]>([]);
  const [showEventForm, setShowEventForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<VaultTimeline | null>(null);
  const [eventForm, setEventForm] = useState<Partial<VaultTimeline>>({});

  // 剧情承诺库
  const [commitments, setCommitments] = useState<VaultPlotPromise[]>([]);
  const [showCommitmentForm, setShowCommitmentForm] = useState(false);
  const [editingCommitment, setEditingCommitment] = useState<VaultPlotPromise | null>(null);
  const [commitmentForm, setCommitmentForm] = useState<Partial<VaultPlotPromise>>({});

  // 世界观库
  const [entries, setEntries] = useState<VaultWorld[]>([]);
  const [showEntryForm, setShowEntryForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState<VaultWorld | null>(null);
  const [entryForm, setEntryForm] = useState<Partial<VaultWorld>>({});

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 加载数据
  useEffect(() => {
    loadData();
  }, [activeTab, projectId]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'characters') {
        const res = await vaultApi.getCharacters(projectId);
        setCharacters(res.data as any);
      } else if (activeTab === 'timeline') {
        const res = await vaultApi.getTimeline(projectId);
        setEvents(res.data as any);
      } else if (activeTab === 'commitments') {
        const res = await vaultApi.getPlotPromises(projectId);
        setCommitments(res.data as any);
      } else if (activeTab === 'worldview') {
        const res = await vaultApi.getWorld(projectId);
        setEntries(res.data as any);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
      showMessage('error', '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  // 角色 CRUD
  const handleCreateCharacter = async () => {
    try {
      await vaultApi.createCharacter(projectId, characterForm as any);
      showMessage('success', '角色已创建');
      setShowCharacterForm(false);
      setCharacterForm({ name: '', role: 'mc' });
      loadData();
    } catch (error) {
      console.error('创建失败:', error);
      showMessage('error', '创建失败');
    }
  };

  const handleUpdateCharacter = async () => {
    if (!editingCharacter) return;
    try {
      await vaultApi.updateCharacter(projectId, editingCharacter.id, characterForm as any);
      showMessage('success', '角色已更新');
      setEditingCharacter(null);
      setCharacterForm({ name: '', role: 'mc' });
      loadData();
    } catch (error) {
      console.error('更新失败:', error);
      showMessage('error', '更新失败');
    }
  };

  const handleDeleteCharacter = async (id: string) => {
    if (!confirm('确定要删除此角色吗？')) return;
    try {
      await vaultApi.deleteCharacter(projectId, id);
      showMessage('success', '角色已删除');
      loadData();
    } catch (error) {
      console.error('删除失败:', error);
      showMessage('error', '删除失败');
    }
  };

  // 时间线 CRUD
  const handleCreateEvent = async () => {
    try {
      await vaultApi.createTimelineEvent(projectId, eventForm as any);
      showMessage('success', '时间线事件已创建');
      setShowEventForm(false);
      setEventForm({});
      loadData();
    } catch (error) {
      console.error('创建失败:', error);
      showMessage('error', '创建失败');
    }
  };

  const handleDeleteEvent = async (id: string) => {
    if (!confirm('确定要删除此事件吗？')) return;
    try {
      await vaultApi.deleteTimelineEvent(projectId, id);
      showMessage('success', '事件已删除');
      loadData();
    } catch (error) {
      console.error('删除失败:', error);
      showMessage('error', '删除失败');
    }
  };

  // 剧情承诺 CRUD
  const handleCreateCommitment = async () => {
    try {
      await vaultApi.createPlotPromise(projectId, commitmentForm as any);
      showMessage('success', '剧情承诺已创建');
      setShowCommitmentForm(false);
      setCommitmentForm({});
      loadData();
    } catch (error) {
      console.error('创建失败:', error);
      showMessage('error', '创建失败');
    }
  };

  const handleDeleteCommitment = async (id: string) => {
    if (!confirm('确定要删除此剧情承诺吗？')) return;
    try {
      await vaultApi.deletePlotPromise(projectId, id);
      showMessage('success', '剧情承诺已删除');
      loadData();
    } catch (error) {
      console.error('删除失败:', error);
      showMessage('error', '删除失败');
    }
  };

  // 世界观 CRUD
  const handleCreateEntry = async () => {
    try {
      await vaultApi.createWorldEntry(projectId, entryForm as any);
      showMessage('success', '世界观条目已创建');
      setShowEntryForm(false);
      setEntryForm({});
      loadData();
    } catch (error) {
      console.error('创建失败:', error);
      showMessage('error', '创建失败');
    }
  };

  const handleDeleteEntry = async (id: string) => {
    if (!confirm('确定要删除此条目吗？')) return;
    try {
      await vaultApi.deleteWorldEntry(projectId, id);
      showMessage('success', '条目已删除');
      loadData();
    } catch (error) {
      console.error('删除失败:', error);
      showMessage('error', '删除失败');
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>四库管理</h1>
        <div className={styles.projectId}>项目 ID: {projectId}</div>
      </div>

      {message && (
        <div className={`${styles.message} ${styles[`message${message.type.charAt(0).toUpperCase() + message.type.slice(1)}`]}`}>
          {message.text}
        </div>
      )}

      <div className={styles.content}>
        {/* Tab 栏 */}
        <div className={styles.tabs}>
          {['characters', 'timeline', 'commitments', 'worldview'].map(tab => (
            <button
              key={tab}
              className={`${styles.tab} ${activeTab === tab ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(tab as any)}
            >
              {tab === 'characters' && '👥 人物库'}
              {tab === 'timeline' && '⏱️ 时间线库'}
              {tab === 'commitments' && '📖 剧情承诺库'}
              {tab === 'worldview' && '🌍 世界观库'}
            </button>
          ))}
        </div>

        {/* 内容区 */}
        <div className={styles.main}>
          {/* 人物库 */}
          {activeTab === 'characters' && (
            <div className={styles.tabContent}>
              <div className={styles.toolbar}>
                <button
                  className={styles.createBtn}
                  onClick={() => setShowCharacterForm(true)}
                >
                  ＋ 创建角色
                </button>
              </div>

              {showCharacterForm && (
                <div className={styles.formCard}>
                  <h3>{editingCharacter ? '编辑角色' : '创建角色'}</h3>
                  <div className={styles.formGroup}>
                    <label>名称</label>
                    <input
                      type="text"
                      value={characterForm.name}
                      onChange={e => setCharacterForm({ ...characterForm, name: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>角色</label>
                    <select
                      value={characterForm.role}
                      onChange={e => setCharacterForm({ ...characterForm, role: e.target.value as any })}
                    >
                      <option value="mc">主角</option>
                      <option value="ally">盟友</option>
                      <option value="enemy">对手</option>
                      <option value="neutral">中立</option>
                    </select>
                  </div>
                  <div className={styles.formActions}>
                    <button
                      className={styles.saveBtn}
                      onClick={editingCharacter ? handleUpdateCharacter : handleCreateCharacter}
                    >
                      {editingCharacter ? '更新' : '创建'}
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setShowCharacterForm(false);
                        setEditingCharacter(null);
                        setCharacterForm({ name: '', role: 'mc' });
                      }}
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.list}>
                {loading ? (
                  <div className={styles.loading}>加载中...</div>
                ) : characters.length === 0 ? (
                  <div className={styles.empty}>暂无角色</div>
                ) : (
                  characters.map(char => (
                    <div key={char.id} className={styles.card}>
                      <div className={styles.cardHeader}>
                        <div className={styles.cardAvatar}>{char.name[0]}</div>
                        <div>
                          <div className={styles.cardName}>{char.name}</div>
                          <span className={styles.cardBadge}>
                            {char.role === 'mc' ? '主角' : char.role === 'ally' ? '盟友' : char.role === 'enemy' ? '对手' : '中立'}
                          </span>
                        </div>
                      </div>
                      <div className={styles.cardLocation}>
                        <div>位置：{char.location}</div>
                      </div>
                      <div className={styles.cardActions}>
                        <button
                          className={styles.editBtn}
                          onClick={() => {
                            setEditingCharacter(char);
                            setCharacterForm({
                              name: char.name,
                              role: char.role,
                              location: char.location,
                            });
                            setShowCharacterForm(true);
                          }}
                        >
                          编辑
                        </button>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleDeleteCharacter(char.id)}
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 时间线库 */}
          {activeTab === 'timeline' && (
            <div className={styles.tabContent}>
              <div className={styles.toolbar}>
                <button
                  className={styles.createBtn}
                  onClick={() => setShowEventForm(true)}
                >
                  ＋ 创建事件
                </button>
              </div>

              {showEventForm && (
                <div className={styles.formCard}>
                  <h3>创建时间线事件</h3>
                  <div className={styles.formGroup}>
                    <label>天数</label>
                    <input
                      type="number"
                      value={eventForm.day || ''}
                      onChange={e => setEventForm({ ...eventForm, day: parseInt(e.target.value) })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>标题</label>
                    <input
                      type="text"
                      value={eventForm.title || ''}
                      onChange={e => setEventForm({ ...eventForm, title: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>描述</label>
                    <textarea
                      value={eventForm.description || ''}
                      onChange={e => setEventForm({ ...eventForm, description: e.target.value })}
                    />
                  </div>
                  <div className={styles.formActions}>
                    <button className={styles.saveBtn} onClick={handleCreateEvent}>
                      创建
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setShowEventForm(false);
                        setEventForm({});
                      }}
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.list}>
                {loading ? (
                  <div className={styles.loading}>加载中...</div>
                ) : events.length === 0 ? (
                  <div className={styles.empty}>暂无事件</div>
                ) : (
                  events.map(event => (
                    <div key={event.id} className={styles.card}>
                      <div className={styles.cardTitle}>
                        第{event.day}天 · {event.title}
                      </div>
                      <div className={styles.cardDesc}>{event.description}</div>
                      <div className={styles.cardActions}>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleDeleteEvent(event.id)}
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 剧情承诺库 */}
          {activeTab === 'commitments' && (
            <div className={styles.tabContent}>
              <div className={styles.toolbar}>
                <button
                  className={styles.createBtn}
                  onClick={() => setShowCommitmentForm(true)}
                >
                  ＋ 创建承诺
                </button>
              </div>

              {showCommitmentForm && (
                <div className={styles.formCard}>
                  <h3>创建剧情承诺</h3>
                  <div className={styles.formGroup}>
                    <label>类型</label>
                    <select
                      value={commitmentForm.type || 'foreshadow'}
                      onChange={e => setCommitmentForm({ ...commitmentForm, type: e.target.value as any })}
                    >
                      <option value="foreshadow">伏笔</option>
                      <option value="arc">弧线</option>
                      <option value="subplot">支线</option>
                      <option value="theme">主题</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label>标题</label>
                    <input
                      type="text"
                      value={commitmentForm.title || ''}
                      onChange={e => setCommitmentForm({ ...commitmentForm, title: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>状态</label>
                    <select
                      value={commitmentForm.status || 'pending'}
                      onChange={e => setCommitmentForm({ ...commitmentForm, status: e.target.value as any })}
                    >
                      <option value="pending">待处理</option>
                      <option value="active">活跃</option>
                      <option value="recycled">已回收</option>
                      <option value="abandoned">已放弃</option>
                    </select>
                  </div>
                  <div className={styles.formActions}>
                    <button className={styles.saveBtn} onClick={handleCreateCommitment}>
                      创建
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setShowCommitmentForm(false);
                        setCommitmentForm({});
                      }}
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.list}>
                {loading ? (
                  <div className={styles.loading}>加载中...</div>
                ) : commitments.length === 0 ? (
                  <div className={styles.empty}>暂无承诺</div>
                ) : (
                  commitments.map(item => (
                    <div key={item.id} className={styles.card}>
                      <div className={styles.cardTitle}>{item.title}</div>
                      <div className={styles.cardType}>
                        {item.type === 'foreshadow' ? '伏笔' : item.type === 'arc' ? '弧线' : item.type === 'subplot' ? '支线' : '主题'}
                      </div>
                      <div className={styles.cardStatus}>状态：{item.status}</div>
                      <div className={styles.cardActions}>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleDeleteCommitment(item.id)}
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 世界观库 */}
          {activeTab === 'worldview' && (
            <div className={styles.tabContent}>
              <div className={styles.toolbar}>
                <button
                  className={styles.createBtn}
                  onClick={() => setShowEntryForm(true)}
                >
                  ＋ 创建条目
                </button>
              </div>

              {showEntryForm && (
                <div className={styles.formCard}>
                  <h3>创建世界观条目</h3>
                  <div className={styles.formGroup}>
                    <label>分类</label>
                    <select
                      value={entryForm.category || 'rule'}
                      onChange={e => setEntryForm({ ...entryForm, category: e.target.value as any })}
                    >
                      <option value="rule">世界规则</option>
                      <option value="location">地点</option>
                      <option value="item">重要物品</option>
                      <option value="faction">势力关系</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label>名称</label>
                    <input
                      type="text"
                      value={entryForm.name || ''}
                      onChange={e => setEntryForm({ ...entryForm, name: e.target.value })}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>描述</label>
                    <textarea
                      value={entryForm.description || ''}
                      onChange={e => setEntryForm({ ...entryForm, description: e.target.value })}
                    />
                  </div>
                  <div className={styles.formActions}>
                    <button className={styles.saveBtn} onClick={handleCreateEntry}>
                      创建
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setShowEntryForm(false);
                        setEntryForm({});
                      }}
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              <div className={styles.list}>
                {loading ? (
                  <div className={styles.loading}>加载中...</div>
                ) : entries.length === 0 ? (
                  <div className={styles.empty}>暂无条目</div>
                ) : (
                  entries.map(entry => (
                    <div key={entry.id} className={styles.card}>
                      <div className={styles.cardTitle}>{entry.name}</div>
                      <div className={styles.cardType}>
                        {entry.category === 'rule' ? '世界规则' : entry.category === 'location' ? '地点' : entry.category === 'item' ? '重要物品' : '势力关系'}
                      </div>
                      <div className={styles.cardDesc}>{entry.description}</div>
                      <div className={styles.cardActions}>
                        <button
                          className={styles.deleteBtn}
                          onClick={() => handleDeleteEntry(entry.id)}
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
