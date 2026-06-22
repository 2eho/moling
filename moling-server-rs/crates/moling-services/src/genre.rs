//! Genre (拆书引擎) — chapter analysis pipeline for genre profile extraction.
//!
//! Mirrors Python `app/genre/` (A1-A5 pipeline + ColdStartLoader).
//! Pipeline: A1 Opening → A2 Characters → A3 Hooks → A4 Rhythm → A5 Profile.
//!
//! Also provides `ColdStartLoader` for project prefill from analysed genre archetypes.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::LazyLock;

// ---------------------------------------------------------------------------
// Data models (mirrors Python app/genre/models.py)
// ---------------------------------------------------------------------------

/// The final output of the genre analysis pipeline.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenreProfile {
    pub genre: String,
    pub version: String,
    pub chapters_analyzed: usize,
    pub novels_analyzed: usize,
    pub golden_three_structure: GoldenThreeStructure,
    pub character_archetypes: Vec<CharacterArchetype>,
    pub world_templates: Vec<WorldTemplate>,
    pub pacing_curve: PacingCurve,
    pub card_pool_enrichment: Vec<CardTemplate>,
    pub dynamic_layer_seeds: DynamicLayerSeeds,
    pub style_fingerprint: StyleFingerprintData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoldenThreeStructure {
    pub opening_pattern: String,
    pub pattern_confidence: f64,
    pub attraction_score: f64,
    pub initial_rhythm: Vec<RhythmPoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RhythmPoint {
    pub chapter: usize,
    pub paragraph: usize,
    pub word_count: usize,
    pub dialogue_ratio: f64,
    pub hooks_per_1k: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterArchetype {
    pub name: String,
    pub role: String,
    pub traits: Vec<String>,
    pub entry_chapter: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorldTemplate {
    pub name: String,
    pub category: String,
    pub traits: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PacingCurve {
    pub chapters: Vec<f64>,
    pub density: Vec<f64>,
    pub average_density: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CardTemplate {
    pub card_name: String,
    pub direction_text: String,
    pub rarity: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DynamicLayerSeeds {
    pub must_hold: Vec<String>,
    pub must_not: Vec<String>,
    pub hooks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StyleFingerprintData {
    pub avg_sentence_length: f64,
    pub dialogue_ratio: f64,
    pub paragraph_length: f64,
    pub vocabulary_richness: f64,
}

// ---------------------------------------------------------------------------
// A1 Result types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpeningPattern {
    pub pattern_type: String,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A1Result {
    pub opening_pattern: OpeningPattern,
    pub rhythm_curve: Vec<A1RhythmPoint>,
    pub attraction_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A1RhythmPoint {
    pub chapter: usize,
    pub word_count: usize,
    pub dialogue_ratio: f64,
    pub conflict_density: f64,
}

// ---------------------------------------------------------------------------
// A2-A4 Result types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A2Result {
    pub characters: Vec<CharacterArchetype>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3Result {
    pub density_curve: Vec<f64>,
    pub total_hooks: usize,
    pub hook_types: HashMap<String, usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A4Result {
    pub pacing_curve: PacingCurve,
    pub rhythm_pattern: String,
}

// ---------------------------------------------------------------------------
// ColdStart / Prefill types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrefillResult {
    pub vault_prefill: VaultPrefill,
    pub dynamic_layer_prefill: DynamicLayerPrefill,
    pub card_prefill: Vec<CardPrefill>,
    pub character_prototypes: Vec<CharacterPrototype>,
    pub genre_profile: GenreProfile,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultPrefill {
    pub characters: Vec<CharacterProto>,
    pub timeline_events: Vec<TimelineProto>,
    pub plot_promises: Vec<PlotPromiseProto>,
    pub world_entries: Vec<WorldProto>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterProto {
    pub name: String,
    pub role: String,
    pub traits: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelineProto {
    pub description: String,
    pub chapter_hint: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlotPromiseProto {
    pub description: String,
    pub state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorldProto {
    pub name: String,
    pub category: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DynamicLayerPrefill {
    pub must_hold: Vec<String>,
    pub must_not: Vec<String>,
    pub hooks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CardPrefill {
    pub name: String,
    pub direction_text: String,
    pub rarity: String,
    pub direction_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterPrototype {
    pub name: String,
    pub role: String,
    pub traits: Vec<String>,
    pub entry_chapter: usize,
}

// ---------------------------------------------------------------------------
// Known genre list
// ---------------------------------------------------------------------------

pub const KNOWN_GENRES: &[&str] = &[
    "fantasy", "scifi", "romance", "mystery", "horror",
    "historical", "wuxia", "xianxia", "urban", "reality",
];

// ---------------------------------------------------------------------------
// Compiled regex patterns (A1 — opening analysis)
// ---------------------------------------------------------------------------

static HIGH_CONFLICT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:杀|战|逃|追|危|险|斗|攻|挡|死|灭|毁|踹|踢|打|砸|劈|砍|刺|捅|射|爆|轰|抓|掐|勒|锁|扣|压|按|扯|撕|咬|撞|冲|扑|翻|滚|躲|闪|避)").unwrap()
});

static DAILY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:起床|吃饭|教室|办公室|阳光|清晨|学校|家|食堂|街道)").unwrap()
});

static PAST_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:曾经|当年|那年|三年前|往事|回忆起|想起|记得|过去|从前)").unwrap()
});

static DEFINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:叫|称|为|名为|所谓|就是|是指)").unwrap()
});

// A2 — character name patterns (used for alternative matching strategy)
#[allow(dead_code)]
static CHINESE_NAME_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:[\u{4e00}-\u{9fff}]{2,4}(?:·[\u{4e00}-\u{9fff}]{2,4})?)").unwrap()
});

// A3 — hook markers
static HOOK_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:突然|竟然|原来|可是|然而|只是|若是|若是……|忽听|忽见|莫名|不知|为何|疑问|秘密|真相|揭开|发现|不对劲|诡异|奇怪|奇)").unwrap()
});

static CLIFFHANGER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?:……$|——$|？！$|！？$|居然|竟然|没想到)").unwrap()
});

// ---------------------------------------------------------------------------
// GenreService
// ---------------------------------------------------------------------------

/// Service for genre profile analysis and cold-start project prefill.
#[derive(Clone)]
pub struct GenreService;

impl Default for GenreService {
    fn default() -> Self { Self::new() }
}

impl GenreService {
    pub fn new() -> Self {
        Self
    }

    // -- Full pipeline ----------------------------------------------------

    /// Run the complete A1→A2→A3→A4→A5 analysis pipeline.
    pub fn run_full_analysis(
        &self,
        chapters: &[String],
        genre: &str,
        novels_analyzed: usize,
    ) -> GenreProfile {
        // A1: Opening pattern analysis (first 3 chapters)
        let a1 = self.a1_analyze_opening(&chapters[..chapters.len().min(3)]);

        // A2: Character clustering (first 3 chapters)
        let a2 = self.a2_cluster_characters(&chapters[..chapters.len().min(3)]);

        // A3: Hook density quantification (first 5 chapters)
        let a3 = self.a3_quantify_hooks(&chapters[..chapters.len().min(5)]);

        // A4: Rhythm curve fitting
        let a4 = self.a4_fit_rhythm_curve(
            &chapters[..chapters.len().min(5)],
            &a3.density_curve,
        );

        // A5: Pattern summary → GenreProfile
        self.a5_summarize_patterns(&a1, &a2, &a3, &a4, genre, novels_analyzed)
    }

    // -- A1: Opening analysis ---------------------------------------------

    /// Analyze the opening pattern (golden three chapters).
    pub fn a1_analyze_opening(&self, chapters: &[String]) -> A1Result {
        if chapters.is_empty() {
            return A1Result {
                opening_pattern: OpeningPattern {
                    pattern_type: "daily_life".to_string(),
                    confidence: 0.0,
                },
                rhythm_curve: Vec::new(),
                attraction_score: 0.0,
            };
        }

        let ch1_preview = &chapters[0][..chapters[0].len().min(2000)];

        // Score each pattern type
        let scores = [
            ("direct_conflict", self.score_direct_conflict(ch1_preview)),
            ("daily_life", self.score_daily_life(ch1_preview)),
            ("flashback", self.score_flashback(ch1_preview)),
            ("world_building", self.score_world_building(ch1_preview)),
        ];

        let (mut pattern_type, mut confidence) = scores
            .iter()
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(t, c)| (t.to_string(), *c))
            .unwrap_or(("daily_life".to_string(), 0.0));

        // Bias: when direct_conflict and flashback scores are close, prefer conflict
        let conflict_score = scores.iter().find(|(t, _)| *t == "direct_conflict").map(|(_, c)| *c).unwrap_or(0.0);
        let flashback_score = scores.iter().find(|(t, _)| *t == "flashback").map(|(_, c)| *c).unwrap_or(0.0);
        if conflict_score > 0.3 && (conflict_score - flashback_score).abs() <= 0.2 {
            pattern_type = "direct_conflict".to_string();
            confidence = conflict_score;
        }

        // Initial rhythm curve
        let rhythm_curve = self.compute_initial_rhythm(&chapters[..chapters.len().min(3)]);

        // Attraction score
        let attraction = self.compute_attraction(&pattern_type, confidence, &rhythm_curve);

        A1Result {
            opening_pattern: OpeningPattern {
                pattern_type,
                confidence: (confidence * 100.0).round() / 100.0,
            },
            rhythm_curve,
            attraction_score: (attraction * 100.0).round() / 100.0,
        }
    }

    fn score_direct_conflict(&self, text: &str) -> f64 {
        let ch_count = text.chars().count() as f64;
        if ch_count == 0.0 {
            return 0.0;
        }
        let conflicts = HIGH_CONFLICT_RE.find_iter(text).count() as f64;
        let density = conflicts / ch_count * 1000.0;
        if density > 5.0 { 1.0 } else if density > 2.0 { 0.7 + (density - 2.0) * 0.1 } else { density * 0.35 }
    }

    fn score_daily_life(&self, text: &str) -> f64 {
        let ch_count = text.chars().count() as f64;
        if ch_count == 0.0 {
            return 0.0;
        }
        let daily = DAILY_RE.find_iter(text).count() as f64;
        let density = daily / ch_count * 1000.0;
        if density > 4.0 { 1.0 } else if density > 1.0 { 0.5 + (density - 1.0) * 0.167 } else { density * 0.5 }
    }

    fn score_flashback(&self, text: &str) -> f64 {
        let ch_count = text.chars().count() as f64;
        if ch_count == 0.0 {
            return 0.0;
        }
        let past = PAST_RE.find_iter(text).count() as f64;
        let density = past / ch_count * 1000.0;
        if density > 3.0 { 1.0 } else if density > 1.0 { 0.4 + (density - 1.0) * 0.3 } else { density * 0.4 }
    }

    fn score_world_building(&self, text: &str) -> f64 {
        let ch_count = text.chars().count() as f64;
        if ch_count == 0.0 {
            return 0.0;
        }
        let defines = DEFINE_RE.find_iter(text).count() as f64;
        let density = defines / ch_count * 1000.0;
        if density > 3.0 { 1.0 } else if density > 1.0 { 0.5 + (density - 1.0) * 0.25 } else { density * 0.5 }
    }

    fn compute_initial_rhythm(&self, chapters: &[String]) -> Vec<A1RhythmPoint> {
        chapters.iter().enumerate().map(|(i, ch)| {
            let chars = ch.chars().count();
            let dialogue_chars = ch.chars().filter(|c| *c == '"' || *c == '\u{201c}' || *c == '\u{201d}' || *c == '\u{300c}' || *c == '\u{300d}').count();
            let dialogue_ratio = if chars > 0 { dialogue_chars as f64 / chars as f64 } else { 0.0 };
            let conflict_count = HIGH_CONFLICT_RE.find_iter(ch).count() as f64;
            let conflict_density = if chars > 0 { conflict_count / chars as f64 * 1000.0 } else { 0.0 };
            A1RhythmPoint {
                chapter: i + 1,
                word_count: chars,
                dialogue_ratio: (dialogue_ratio * 100.0).round() / 100.0,
                conflict_density: (conflict_density * 100.0).round() / 100.0,
            }
        }).collect()
    }

    fn compute_attraction(&self, pattern_type: &str, confidence: f64, rhythm: &[A1RhythmPoint]) -> f64 {
        let base = confidence * 0.6;
        let conflict_boost = if pattern_type == "direct_conflict" { 0.2 } else { 0.0 };
        let rhythm_avg = if rhythm.is_empty() {
            0.0
        } else {
            rhythm.iter().map(|r| r.conflict_density).sum::<f64>() / rhythm.len() as f64
        };
        let rhythm_score = (rhythm_avg / 10.0).min(0.2);
        base + conflict_boost + rhythm_score
    }

    // -- A2: Character clustering -----------------------------------------

    /// Extract and cluster characters from opening chapters.
    pub fn a2_cluster_characters(&self, chapters: &[String]) -> A2Result {
        let mut name_counts: HashMap<String, usize> = HashMap::new();
        let stop_names: [&str; 19] = ["一个", "什么", "怎么", "这个", "那个", "可以", "自己", "没有", "已经",
            "不过", "不是", "因为", "所以", "如果", "但是", "而且", "虽然", "然而", "我们"];

        for ch in chapters {
            let chars: Vec<char> = ch.chars().collect();
            for len in [2, 3, 4] {
                for window in chars.windows(len) {
                    let s: String = window.iter().collect();
                    if s.chars().all(|c| ('\u{4e00}'..='\u{9fff}').contains(&c) || c == '·') {
                        if !stop_names.contains(&s.as_str()) {
                            *name_counts.entry(s).or_insert(0) += 1;
                        }
                    }
                }
            }
        }

        let mut sorted: Vec<_> = name_counts.into_iter()
            .filter(|(_, count)| *count >= 2)
            .collect();
        sorted.sort_by(|a, b| b.1.cmp(&a.1));
        sorted.truncate(10);

        let characters = sorted.into_iter().map(|(name, count)| {
            let role = if count >= 5 { "protagonist" } else if count >= 3 { "supporting" } else { "minor" };
            CharacterArchetype {
                name,
                role: role.to_string(),
                traits: Vec::new(),
                entry_chapter: 1,
            }
        }).collect();

        A2Result { characters }
    }

    // -- A3: Hook density -------------------------------------------------

    /// Quantify hook density across chapters.
    pub fn a3_quantify_hooks(&self, chapters: &[String]) -> A3Result {
        let mut density_curve = Vec::with_capacity(chapters.len());
        let mut hook_types: HashMap<String, usize> = HashMap::new();
        let mut total_hooks = 0usize;

        for ch in chapters {
            let chars = ch.chars().count();
            let hooks = HOOK_RE.find_iter(ch).count();
            let cliffhangers = CLIFFHANGER_RE.find_iter(ch).count();
            let density = if chars > 0 {
                (hooks + cliffhangers) as f64 / chars as f64 * 1000.0
            } else {
                0.0
            };
            density_curve.push((density * 100.0).round() / 100.0);
            total_hooks += hooks + cliffhangers;
        }

        hook_types.insert("hook".to_string(), total_hooks / chapters.len().max(1));
        hook_types.insert("cliffhanger".to_string(), total_hooks);

        A3Result {
            density_curve,
            total_hooks,
            hook_types,
        }
    }

    // -- A4: Rhythm curve -------------------------------------------------

    /// Fit a pacing rhythm curve based on chapter length and hook density.
    pub fn a4_fit_rhythm_curve(&self, chapters: &[String], density_curve: &[f64]) -> A4Result {
        let chapters_vec: Vec<f64> = (1..=chapters.len()).map(|i| i as f64).collect();
        let density = density_curve.to_vec();
        let avg_density = if density.is_empty() { 0.0 } else { density.iter().sum::<f64>() / density.len() as f64 };

        let rhythm_pattern = if avg_density > 3.0 {
            "fast_paced"
        } else if avg_density > 1.5 {
            "balanced"
        } else {
            "slow_burn"
        };

        A4Result {
            pacing_curve: PacingCurve {
                chapters: chapters_vec,
                density,
                average_density: (avg_density * 100.0).round() / 100.0,
            },
            rhythm_pattern: rhythm_pattern.to_string(),
        }
    }

    // -- A5: Profile summary ----------------------------------------------

    /// Generate the final GenreProfile from A1-A4 results.
    pub fn a5_summarize_patterns(
        &self,
        a1: &A1Result,
        a2: &A2Result,
        a3: &A3Result,
        a4: &A4Result,
        genre: &str,
        novels_analyzed: usize,
    ) -> GenreProfile {
        let golden_three = GoldenThreeStructure {
            opening_pattern: a1.opening_pattern.pattern_type.clone(),
            pattern_confidence: a1.opening_pattern.confidence,
            attraction_score: a1.attraction_score,
            initial_rhythm: a1.rhythm_curve.iter().enumerate().map(|(i, p)| RhythmPoint {
                chapter: i + 1,
                paragraph: 0,
                word_count: p.word_count,
                dialogue_ratio: p.dialogue_ratio,
                hooks_per_1k: a3.density_curve.get(i).copied().unwrap_or(0.0),
            }).collect(),
        };

        // Card pool enrichment from character archetypes
        let card_enrichment = a2.characters.iter().take(5).map(|c| CardTemplate {
            card_name: format!("{}出场", c.name),
            direction_text: format!("引入角色 {} ({})", c.name, c.role),
            rarity: if c.role == "protagonist" { "epic".to_string() } else { "common".to_string() },
        }).collect();

        // Dynamic layer seeds
        let dl_seeds = DynamicLayerSeeds {
            must_hold: vec![
                format!("开头模式: {}", a1.opening_pattern.pattern_type),
                format!("节奏类型: {}", a4.rhythm_pattern),
            ],
            must_not: vec!["无铺垫跳跃".to_string(), "节奏断层".to_string()],
            hooks: a3.hook_types.keys().cloned().collect(),
        };

        // Style fingerprint
        let style = StyleFingerprintData {
            avg_sentence_length: 25.0,
            dialogue_ratio: a1.rhythm_curve.first().map(|r| r.dialogue_ratio).unwrap_or(0.3),
            paragraph_length: 120.0,
            vocabulary_richness: 0.65,
        };

        GenreProfile {
            genre: genre.to_string(),
            version: "0.1".to_string(),
            chapters_analyzed: a3.density_curve.len(),
            novels_analyzed,
            golden_three_structure: golden_three,
            character_archetypes: a2.characters.clone(),
            world_templates: Vec::new(),
            pacing_curve: a4.pacing_curve.clone(),
            card_pool_enrichment: card_enrichment,
            dynamic_layer_seeds: dl_seeds,
            style_fingerprint: style,
        }
    }

    // -- ColdStart / Prefill ----------------------------------------------

    /// Generate a prefill result from a genre profile for cold-start project creation.
    pub fn generate_prefill(&self, profile: &GenreProfile) -> PrefillResult {
        let vault = VaultPrefill {
            characters: profile.character_archetypes.iter().map(|c| CharacterProto {
                name: c.name.clone(),
                role: c.role.clone(),
                traits: c.traits.clone(),
            }).collect(),
            timeline_events: Vec::new(),
            plot_promises: Vec::new(),
            world_entries: profile.world_templates.iter().map(|w| WorldProto {
                name: w.name.clone(),
                category: w.category.clone(),
                description: w.traits.join("、"),
            }).collect(),
        };

        let dl = DynamicLayerPrefill {
            must_hold: profile.dynamic_layer_seeds.must_hold.clone(),
            must_not: profile.dynamic_layer_seeds.must_not.clone(),
            hooks: profile.dynamic_layer_seeds.hooks.clone(),
        };

        let cards: Vec<CardPrefill> = profile.card_pool_enrichment.iter().map(|c| CardPrefill {
            name: c.card_name.clone(),
            direction_text: c.direction_text.clone(),
            rarity: c.rarity.clone(),
            direction_type: "character".to_string(),
        }).collect();

        let prototypes = profile.character_archetypes.iter().map(|c| CharacterPrototype {
            name: c.name.clone(),
            role: c.role.clone(),
            traits: c.traits.clone(),
            entry_chapter: c.entry_chapter,
        }).collect();

        PrefillResult {
            vault_prefill: vault,
            dynamic_layer_prefill: dl,
            card_prefill: cards,
            character_prototypes: prototypes,
            genre_profile: profile.clone(),
        }
    }

    /// Get pre-built genre archetypes for a known genre.
    pub fn get_genre_archetype(&self, genre: &str) -> Option<GenreProfile> {
        match genre.to_lowercase().as_str() {
            "fantasy" | "玄幻" | "xuanhuan" => Some(self.build_fantasy_archetype()),
            "wuxia" | "武侠" => Some(self.build_wuxia_archetype()),
            "xianxia" | "仙侠" => Some(self.build_xianxia_archetype()),
            "urban" | "都市" => Some(self.build_urban_archetype()),
            "scifi" | "科幻" => Some(self.build_scifi_archetype()),
            "romance" | "言情" => Some(self.build_romance_archetype()),
            _ => None,
        }
    }

    fn build_fantasy_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "fantasy".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "world_building".to_string(),
                pattern_confidence: 0.75, attraction_score: 0.68,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: vec![
                CharacterArchetype { name: "主角".into(), role: "protagonist".into(), traits: vec!["天赋异禀".into(), "身世神秘".into()], entry_chapter: 1 },
                CharacterArchetype { name: "导师".into(), role: "supporting".into(), traits: vec!["深不可测".into(), "引导者".into()], entry_chapter: 2 },
            ],
            world_templates: vec![
                WorldTemplate { name: "修炼体系".into(), category: "power_system".into(), traits: vec!["等级分明".into(), "突破瓶颈".into()] },
            ],
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![2.5, 3.0, 2.8], average_density: 2.77 },
            card_pool_enrichment: vec![
                CardTemplate { card_name: "奇遇".into(), direction_text: "主角获得意外机缘".into(), rarity: "rare".into() },
                CardTemplate { card_name: "战斗".into(), direction_text: "与同级对手交锋".into(), rarity: "common".into() },
            ],
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["升级体系一致性".into()],
                must_not: vec!["战力崩坏".into()],
                hooks: vec!["突破".into(), "奇遇".into(), "战斗".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 22.0, dialogue_ratio: 0.35, paragraph_length: 100.0, vocabulary_richness: 0.6,
            },
        }
    }

    fn build_wuxia_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "wuxia".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "direct_conflict".to_string(),
                pattern_confidence: 0.82, attraction_score: 0.75,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: vec![
                CharacterArchetype { name: "少侠".into(), role: "protagonist".into(), traits: vec!["武学奇才".into(), "侠义心肠".into()], entry_chapter: 1 },
            ],
            world_templates: vec![
                WorldTemplate { name: "江湖".into(), category: "setting".into(), traits: vec!["帮派林立".into(), "恩怨情仇".into()] },
            ],
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![3.5, 2.8, 3.2], average_density: 3.17 },
            card_pool_enrichment: Vec::new(),
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["武功境界体系".into()],
                must_not: vec!["实力跳跃过大".into()],
                hooks: vec!["复仇".into(), "秘笈".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 18.0, dialogue_ratio: 0.4, paragraph_length: 80.0, vocabulary_richness: 0.55,
            },
        }
    }

    fn build_xianxia_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "xianxia".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "world_building".to_string(),
                pattern_confidence: 0.78, attraction_score: 0.72,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: vec![
                CharacterArchetype { name: "修士".into(), role: "protagonist".into(), traits: vec!["灵根非凡".into(), "机缘不断".into()], entry_chapter: 1 },
            ],
            world_templates: vec![
                WorldTemplate { name: "修真界".into(), category: "setting".into(), traits: vec!["灵气复苏".into(), "宗门林立".into()] },
            ],
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![2.0, 3.5, 2.5], average_density: 2.67 },
            card_pool_enrichment: Vec::new(),
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["境界体系".into()],
                must_not: vec!["跨境界碾压".into()],
                hooks: vec!["渡劫".into(), "机缘".into(), "秘境".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 20.0, dialogue_ratio: 0.3, paragraph_length: 90.0, vocabulary_richness: 0.58,
            },
        }
    }

    fn build_urban_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "urban".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "daily_life".to_string(),
                pattern_confidence: 0.7, attraction_score: 0.6,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: vec![
                CharacterArchetype { name: "主角".into(), role: "protagonist".into(), traits: vec!["社畜".into(), "隐藏能力".into()], entry_chapter: 1 },
            ],
            world_templates: vec![
                WorldTemplate { name: "都市".into(), category: "setting".into(), traits: vec!["现代".into(), "职场".into()] },
            ],
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![1.5, 2.0, 1.8], average_density: 1.77 },
            card_pool_enrichment: Vec::new(),
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["现代科技水平".into()],
                must_not: vec!["科技降级".into()],
                hooks: vec!["逆袭".into(), "商战".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 18.0, dialogue_ratio: 0.5, paragraph_length: 70.0, vocabulary_richness: 0.5,
            },
        }
    }

    fn build_scifi_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "scifi".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "world_building".to_string(),
                pattern_confidence: 0.85, attraction_score: 0.78,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: Vec::new(),
            world_templates: vec![
                WorldTemplate { name: "未来世界".into(), category: "setting".into(), traits: vec!["高科技".into(), "星际".into()] },
            ],
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![2.2, 3.0, 2.5], average_density: 2.57 },
            card_pool_enrichment: Vec::new(),
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["科技设定一致性".into()],
                must_not: vec!["科技降级".into()],
                hooks: vec!["发明".into(), "危机".into(), "发现".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 24.0, dialogue_ratio: 0.3, paragraph_length: 110.0, vocabulary_richness: 0.7,
            },
        }
    }

    fn build_romance_archetype(&self) -> GenreProfile {
        GenreProfile {
            genre: "romance".to_string(), version: "0.1".to_string(),
            chapters_analyzed: 0, novels_analyzed: 1,
            golden_three_structure: GoldenThreeStructure {
                opening_pattern: "daily_life".to_string(),
                pattern_confidence: 0.72, attraction_score: 0.65,
                initial_rhythm: Vec::new(),
            },
            character_archetypes: vec![
                CharacterArchetype { name: "女主".into(), role: "protagonist".into(), traits: vec!["独立".into(), "有主见".into()], entry_chapter: 1 },
                CharacterArchetype { name: "男主".into(), role: "supporting".into(), traits: vec!["高冷".into(), "深情".into()], entry_chapter: 2 },
            ],
            world_templates: Vec::new(),
            pacing_curve: PacingCurve { chapters: vec![1.0, 2.0, 3.0], density: vec![2.0, 2.5, 2.2], average_density: 2.23 },
            card_pool_enrichment: Vec::new(),
            dynamic_layer_seeds: DynamicLayerSeeds {
                must_hold: vec!["感情线主线".into()],
                must_not: vec!["感情跳跃".into()],
                hooks: vec!["误会".into(), "告白".into(), "重逢".into()],
            },
            style_fingerprint: StyleFingerprintData {
                avg_sentence_length: 16.0, dialogue_ratio: 0.55, paragraph_length: 60.0, vocabulary_richness: 0.45,
            },
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_chapters() -> Vec<String> {
        vec![
            "第一章 天降异象\n\n天空突然撕裂，一道金光直直砸向少年林风。他正在家吃饭，完全没有防备。\
             那金光砸落在地，竟是一柄古朴长剑。林风颤抖着伸手去抓，却发现剑身上刻着\"屠天\"二字。\
             突然，一道黑影从旁闪出！\"把剑交出来！\"来人一脚踢向林风，却被剑光自动挡下。\
             林风被打得翻了个跟头，却感觉体内有什么东西在觉醒……".to_string(),
            "第二章 屠天剑认主\n\n\"此剑名为屠天，乃是上古杀器。\"一个苍老的声音在林风脑海中响起。\
             \"你……你是谁？\"林风惊恐地环顾四周。学校教室里，同学们都在安静自习，没人注意到他的异样。\
             回想当年家族被灭门的那天，林风的心又开始痛了。             \"我会帮你变强，\"那声音说，\"但你要付出代价。\
             所谓的代价，就是你的记忆。每一天，你都会忘记一件最重要的事。\"".to_string(),
            "第三章 第一战\n\n林风逃出校园，却被三个黑衣人追上。\"小子，屠天剑不是你能拿的东西！\"\
             他转身就跑，但对方速度更快。一记劈掌打来，林风本能地抬手格挡——挡下了！\
             他掐住对方手腕，用力一扯，竟将人摔了出去。另外两人围攻上来，林风左躲右闪，\
             每一次闪避都像是身体自己在动。短短五分钟，三人全倒。林风看着自己的手，莫名有种恐惧……".to_string(),
        ]
    }

    #[test]
    fn test_a1_opening_analysis() {
        let svc = GenreService::new();
        let result = svc.a1_analyze_opening(&sample_chapters());
        assert!(result.attraction_score > 0.0);
        assert!(!result.opening_pattern.pattern_type.is_empty());
        assert_eq!(result.rhythm_curve.len(), 3);
    }

    #[test]
    fn test_a1_empty() {
        let svc = GenreService::new();
        let result = svc.a1_analyze_opening(&[]);
        assert_eq!(result.opening_pattern.pattern_type, "daily_life");
        assert_eq!(result.attraction_score, 0.0);
    }

    #[test]
    fn test_a2_character_clustering() {
        let svc = GenreService::new();
        let result = svc.a2_cluster_characters(&sample_chapters());
        // "林风" appears many times, should be protagonist
        assert!(!result.characters.is_empty());
        assert!(result.characters.iter().any(|c| c.name == "林风"));
    }

    #[test]
    fn test_a3_hook_density() {
        let svc = GenreService::new();
        let result = svc.a3_quantify_hooks(&sample_chapters());
        assert_eq!(result.density_curve.len(), 3);
        assert!(result.total_hooks > 0);
    }

    #[test]
    fn test_a4_rhythm_curve() {
        let svc = GenreService::new();
        let a3 = svc.a3_quantify_hooks(&sample_chapters());
        let result = svc.a4_fit_rhythm_curve(&sample_chapters(), &a3.density_curve);
        assert_eq!(result.pacing_curve.chapters.len(), 3);
        assert!(!result.rhythm_pattern.is_empty());
    }

    #[test]
    fn test_full_pipeline() {
        let svc = GenreService::new();
        let profile = svc.run_full_analysis(&sample_chapters(), "fantasy", 1);
        assert_eq!(profile.genre, "fantasy");
        assert_eq!(profile.chapters_analyzed, 3);
        assert_eq!(profile.version, "0.1");
    }

    #[test]
    fn test_get_genre_archetype() {
        let svc = GenreService::new();
        let fantasy = svc.get_genre_archetype("fantasy").unwrap();
        assert_eq!(fantasy.genre, "fantasy");
        assert!(!fantasy.character_archetypes.is_empty());

        let wuxia = svc.get_genre_archetype("wuxia").unwrap();
        assert_eq!(wuxia.genre, "wuxia");

        let unknown = svc.get_genre_archetype("unknown");
        assert!(unknown.is_none());
    }

    #[test]
    fn test_generate_prefill() {
        let svc = GenreService::new();
        let profile = svc.run_full_analysis(&sample_chapters(), "fantasy", 1);
        let prefill = svc.generate_prefill(&profile);
        assert_eq!(prefill.genre_profile.genre, "fantasy");
        assert!(!prefill.vault_prefill.characters.is_empty());
        assert!(prefill.dynamic_layer_prefill.must_hold.len() >= 2);
    }

    #[test]
    fn test_coldstart_archetype_prefill() {
        let svc = GenreService::new();
        let profile = svc.get_genre_archetype("xianxia").unwrap();
        let prefill = svc.generate_prefill(&profile);
        assert_eq!(prefill.genre_profile.genre, "xianxia");
        assert!(prefill.dynamic_layer_prefill.must_not.contains(&"跨境界碾压".to_string()));
    }
}
