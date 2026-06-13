/* ============================================
   墨灵 (Moling) — Mock Vault Data
   ============================================ */

import type {
  VaultCharacter,
  VaultTimeline,
  VaultPlotPromise,
  VaultWorld,
} from "@/lib/types";

export const mockCharacters = [
  {
    id: "char-001",
    project_id: "proj-001",
    name: "林星辰",
    role: "protagonist",
    description: "十六岁少年，青石村普通村民，偶获星穹剑典传承，踏上修真之路。性格坚毅、善良，对未知世界充满好奇。",
    traits: ["坚毅", "善良", "好奇", "执着"],
    background: "自幼父母双亡，由爷爷抚养长大。爷爷曾是修真者，但因伤退出江湖，隐居青石村。",
    arc: "",
    relationships: [
      {
        character_id: "char-002",
        relationship: "青梅竹马",
        description: "与苏月瑶从小一起长大，感情深厚",
      },
    ],
    location: "",
    appearance: "",
    personality: "",
    knowledge: "",
    confidence: 0.5,
  },
  {
    id: "char-002",
    project_id: "proj-001",
    name: "苏月瑶",
    role: "love_interest",
    faction: "青石村",
    status: "active",
    emotion: "温柔",
    traits: ["温柔", "坚强", "敏锐", "善解人意"],
    description: "十五岁少女，林星辰的青梅竹马。体内封印着远古凤族血脉，温柔体贴但内心坚强。",
    background: "来历神秘，被青石村老村长收养。体内凤族血脉是各大势力觊觎的目标。",
    relationships: [
      {
        character_id: "char-001",
        relationship: "青梅竹马",
        description: "与林星辰从小一起长大，暗生情愫",
      },
    ],
    state_machine: {},
    chapter_count: 4,
  },
  {
    id: "char-003",
    project_id: "proj-001",
    name: "楚天行",
    role: "rival",
    faction: "青云宗",
    status: "active",
    emotion: "高傲",
    traits: ["高傲", "天赋异禀", "重情义", "好胜"],
    description: "十八岁，青云宗外门首席弟子，天赋异禀。性格高傲但重情义，与林星辰亦敌亦友。",
    background: "青云宗长老之子，从小被寄予厚望。自视甚高，遇到林星辰后逐渐改变。",
    relationships: [
      {
        character_id: "char-001",
        relationship: "亦敌亦友",
        description: "最初视林星辰为竞争对手，后逐渐认可其实力",
      },
    ],
    state_machine: {},
    chapter_count: 3,
  },
];

export const mockTimelines = [
  {
    id: "tl-001",
    project_id: "proj-001",
    chapter_number: 1,
    event: "获得星穹剑典传承",
    description: "林星辰在青石村后山偶得星穹剑典传承",
    is_key_event: true,
    impact: "开启修真之路",
    characters_involved: ["林星辰"],
  },
  {
    id: "tl-002",
    project_id: "proj-001",
    chapter_number: 2,
    event: "开始修炼，踏入炼气期",
    description: "林星辰开始修炼星穹剑典，成功踏入炼气期一层",
    is_key_event: true,
    impact: "获得修炼基础",
    characters_involved: ["林星辰"],
  },
  {
    id: "tl-003",
    project_id: "proj-001",
    chapter_number: 3,
    event: "参加青石试炼",
    description: "林星辰参加青石村三年一度的试炼，进入迷雾森林",
    is_key_event: true,
    impact: "开启试炼剧情",
    characters_involved: ["林星辰", "苏月瑶"],
  },
  {
    id: "tl-004",
    project_id: "proj-001",
    chapter_number: 3,
    event: "凤族血脉初次显现",
    description: "试炼中苏月瑶的凤族血脉初次显现",
    is_key_event: true,
    impact: "揭示苏月瑶身世线索",
    characters_involved: ["苏月瑶", "林星辰"],
  },
];

export const mockPlotPromises = [
  {
    id: "pp-001",
    project_id: "proj-001",
    description: "林星辰将掌握星穹剑典的全部传承，成就不朽剑仙",
    type: "character_arc",
    status: "active",
    urgency: 3,
    related_characters: ["林星辰"],
    planted_chapter: 1,
    advancement_log: [
      { chapter: 1, event: "获得星穹剑典传承" },
      { chapter: 2, event: "踏入炼气期" },
    ],
  },
  {
    id: "pp-002",
    project_id: "proj-001",
    description: "苏月瑶的凤族血脉真相将被揭开",
    type: "mystery",
    status: "dormant",
    urgency: 4,
    related_characters: ["苏月瑶"],
    planted_chapter: 3,
  },
  {
    id: "pp-003",
    project_id: "proj-001",
    description: "青云宗的秘密阴谋将被公之于众",
    type: "conspiracy",
    status: "dormant",
    urgency: 5,
    planted_chapter: 2,
  },
];

export const mockWorlds = [
  {
    id: "wld-001",
    project_id: "proj-001",
    term: "修真境界体系",
    category: "修炼体系",
    description: "修真境界分为炼气、筑基、金丹、元婴、化神、大乘、渡劫七大境界，每个境界又分前期、中期、后期、圆满四个小境界。",
    rules: [
      "突破大境界时需经历天劫",
      "每个境界寿命增加",
      "高阶修士可压制低阶修士",
    ],
  },
  {
    id: "wld-002",
    project_id: "proj-001",
    term: "星辰之力",
    category: "特殊力量",
    description: "星穹剑典引动的是周天星辰之力，不同于常规的灵气修炼。星辰之力在夜晚最为强大，对修炼者的精神力量要求极高。",
    rules: [
      "夜晚战斗力提升30%",
      "需消耗精神力维持",
      "与星象位置有关",
    ],
  },
];
