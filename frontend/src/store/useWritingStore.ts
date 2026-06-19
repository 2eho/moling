import { create } from 'zustand'

/** 写作阶段 */
export type Phase = 'ideation' | 'outline' | 'character' | 'worldbuilding' | 'drafting' | 'revision'

/** 选项 */
export interface Option {
  id: string
  label: 'A' | 'B' | 'C'
  title: string
  description: string
  preview: string
  agent: string
  confidence: number
}

/** Agent 状态 */
export interface AgentStatus {
  id: string
  name: string
  label: string
  status: 'active' | 'idle' | 'thinking'
}

/** 章节 */
export interface Chapter {
  id: number
  title: string
  summary: string
  content: string
  status: 'draft' | 'completed'
}

/** 人物 */
export interface Character {
  id: string
  name: string
  role: 'protagonist' | 'supporting' | 'antagonist' | 'minor'
  description: string
  arc: string
}

/** 伏笔 */
export interface Foreshadowing {
  id: string
  description: string
  status: 'planted' | 'resolved'
  chapter?: number
}

/** 小说全状态 */
export interface NovelState {
  id: string
  title: string
  genre: string
  phase: Phase
  currentChapter: number
  totalChapters: number
  summary: string
  chapters: Chapter[]
  characters: Character[]
  foreshadowing: Foreshadowing[]
  worldRules: string
  styleNotes: string
}

/** 写作 Store */
interface WritingStore {
  novel: NovelState
  options: Option[]
  selectedOption: string | null
  customInput: string
  agents: AgentStatus[]
  history: { phase: Phase; chapter: number; choice: string }[]
  isGenerating: boolean

  setPhase: (phase: Phase) => void
  setSelectedOption: (id: string | null) => void
  setCustomInput: (input: string) => void
  selectOption: (optionId: string) => void
  submitCustom: () => void
  undo: () => void
  generateOptions: () => void
  updateAgents: (agents: AgentStatus[]) => void
}

/** 阶段中文映射 */
export const PHASE_LABELS: Record<Phase, string> = {
  ideation: '构思',
  outline: '大纲',
  character: '人设',
  worldbuilding: '世界观',
  drafting: '草稿',
  revision: '修订',
}

/** 阶段序号 */
export const PHASE_ORDER: Phase[] = ['ideation', 'outline', 'character', 'worldbuilding', 'drafting', 'revision']

/** 计算阶段进度 (0-100) */
export const getPhaseProgress = (phase: Phase): number => {
  const idx = PHASE_ORDER.indexOf(phase)
  if (idx === -1) return 0
  return Math.round(((idx + 1) / PHASE_ORDER.length) * 100)
}

/** Mock 小说数据 — 《剑道巅峰》 */
const mockNovel: NovelState = {
  id: 'novel-001',
  title: '剑道巅峰',
  genre: '玄幻修仙',
  phase: 'drafting',
  currentChapter: 3,
  totalChapters: 12,
  summary: '少年林风身怀绝世剑骨，却被视为废材。一朝觉醒，踏上逆天改命之路。',
  chapters: [
    { id: 1, title: '废材少年', summary: '林风在宗门大比中被羞辱，剑骨被封。', content: '', status: 'completed' },
    { id: 2, title: '剑骨觉醒', summary: '生死关头，剑骨爆发，林风反败为胜。', content: '', status: 'completed' },
    { id: 3, title: '剑指苍穹', summary: '林风突破金丹期，剑指苍穹派。', content: '', status: 'draft' },
  ],
  characters: [
    { id: 'c1', name: '林风', role: 'protagonist', description: '剑骨传人，金丹期修士', arc: '从废材到剑道至尊' },
    { id: 'c2', name: '苏长老', role: 'supporting', description: '苍穹派内门长老，暗中指导林风', arc: '守护传承' },
    { id: 'c3', name: '暗影宗', role: 'antagonist', description: '神秘黑暗势力，觊觎剑骨之力', arc: '揭开阴谋' },
    { id: 'c4', name: '柳如烟', role: 'supporting', description: '苍穹派大师姐，与林风有婚约', arc: '从轻视到认可' },
  ],
  foreshadowing: [
    { id: 'f1', description: '剑骨的真正来历', status: 'planted' },
    { id: 'f2', description: '苏长老的身份秘密', status: 'planted' },
    { id: 'f3', description: '暗影宗的幕后黑手', status: 'planted' },
  ],
  worldRules: '修仙境界：炼气→筑基→金丹→元婴→化神→渡劫→大乘。剑修独尊。',
  styleNotes: '网文玄幻风格，热血爽文，节奏紧凑，战斗描写细腻。第三人称有限视角，以林风为主。',
}

/** Mock 选项 */
const mockOptions: Option[] = [
  {
    id: 'opt-a',
    label: 'A',
    title: '热血突破 — 林风正面迎敌',
    description: '林风凭借新突破的金丹之力，正面迎战暗影宗的围剿。以一敌百，剑气纵横，震慑群敌。',
    preview: '林风深吸一口气，体内金丹之力如潮水般涌动。他抬眼看向前方黑压压的暗影宗弟子，嘴角勾起一抹冷笑。"来得好，"他低语道，"正好试试我这新力量。"剑光乍起，一道百丈剑芒撕裂长空...',
    agent: 'plot',
    confidence: 0.92,
  },
  {
    id: 'opt-b',
    label: 'B',
    title: '智取为上 — 设局反杀',
    description: '林风识破暗影宗的埋伏，将计就计，利用苏长老提供的阵法反制敌人。智斗为主，展现林风的谋略。',
    preview: '林风察觉到前方树林中微弱的灵力波动。他不动声色，手指暗中掐诀，一道道阵纹无声无息地铺展开来。"想埋伏我？"他心中冷笑，"那就让你们见识见识，什么叫做自投罗网。"方圆百丈的困杀阵悄然成型...',
    agent: 'plot',
    confidence: 0.87,
  },
  {
    id: 'opt-c',
    label: 'C',
    title: '引入变数 — 柳如烟救援',
    description: '林风陷入苦战，关键时刻柳如烟率苍穹派弟子赶到。两人并肩作战，关系发生微妙变化。',
    preview: '林风剑势已老，暗影宗五大护法将他围在核心。就在这时，一道清脆的剑鸣划破天际。"住手！"柳如烟白衣如雪，御剑而来。她看林风的眼神中，第一次没了轻视，取而代之的是一种复杂的情绪...',
    agent: 'character',
    confidence: 0.85,
  },
]

export const useWritingStore = create<WritingStore>((set, get) => ({
  novel: mockNovel,
  options: mockOptions,
  selectedOption: null,
  customInput: '',
  agents: [
    { id: 'plot', name: 'Plot', label: '剧情代理', status: 'active' },
    { id: 'character', name: 'Character', label: '人物代理', status: 'active' },
    { id: 'dialogue', name: 'Dialogue', label: '对话代理', status: 'idle' },
    { id: 'style', name: 'Style', label: '风格代理', status: 'active' },
    { id: 'world', name: 'World', label: '世界观代理', status: 'active' },
  ],
  history: [],
  isGenerating: false,

  setPhase: (phase) => set((s) => ({
    novel: { ...s.novel, phase },
    options: s.options,
    selectedOption: null,
  })),

  setSelectedOption: (id) => set({ selectedOption: id }),

  setCustomInput: (input) => set({ customInput: input }),

  selectOption: (optionId) => {
    const state = get()
    const option = state.options.find((o) => o.id === optionId)
    if (!option) return

    set((s) => ({
      history: [...s.history, { phase: s.novel.phase, chapter: s.novel.currentChapter, choice: option.label }],
      selectedOption: optionId,
      isGenerating: true,
    }))

    // 模拟生成延迟
    setTimeout(() => {
      set({ isGenerating: false })
    }, 1500)
  },

  submitCustom: () => {
    const state = get()
    if (!state.customInput.trim()) return

    set((s) => ({
      history: [...s.history, { phase: s.novel.phase, chapter: s.novel.currentChapter, choice: 'D' }],
      customInput: '',
      isGenerating: true,
    }))

    setTimeout(() => {
      set({ isGenerating: false })
    }, 1500)
  },

  undo: () => {
    const state = get()
    if (state.history.length === 0) return
    set((s) => ({
      history: s.history.slice(0, -1),
      selectedOption: null,
    }))
  },

  generateOptions: () => {
    set({ isGenerating: true })
    setTimeout(() => {
      set({
        options: [
          ...mockOptions.map((o) => ({ ...o, id: o.id + '-' + Date.now() })),
        ],
        isGenerating: false,
      })
    }, 1200)
  },

  updateAgents: (agents) => set({ agents }),
}))
