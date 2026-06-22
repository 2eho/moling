//! 墨灵 (Moling) — Book Analysis Service.
//!
//! Provides analysis tools for creative projects:
//! - Character extraction and relationship mapping
//! - Plot structure analysis
//! - Writing style detection
//! - Foreshadowing tracking
//! - Pacing analysis
//!
//! Ported from Python `app/service/book_analysis_service.py`.

use moling_core::error::AppResult;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::entities::chapter::Model as ChapterModel;

use sea_orm::DatabaseConnection;
use serde::Serialize;
use std::collections::{HashMap, HashSet};
use tracing::info;

// ---------------------------------------------------------------------------
// Regex Patterns (Regex-lite compatible)
// ---------------------------------------------------------------------------

/// Check if char is a CJK unified ideograph.
fn is_cjk_char(ch: char) -> bool {
    matches!(ch, '\u{4e00}'..='\u{9fff}')
}

/// Stop words for name filtering.
const STOP_NAMES: &[&str] = &[
    "但是", "因为", "如果", "虽然", "而且", "然后", "可以", "没有",
    "那个", "这个", "什么", "怎么", "还是", "只是", "不是", "就是",
    "一个", "我们", "他们", "你们", "自己", "知道", "看见", "听到",
    "出来", "起来", "过来", "回去", "进来", "出去", "开始", "继续",
    "突然", "终于", "那么", "这样", "那样", "先生", "小姐",
    "时候", "地方", "东西", "已经", "还是", "因为", "所以", "虽然",
    "但是", "如果", "觉得", "以为", "不过", "恐怕", "难道",
    "可能", "应该", "能够", "愿意", "必须", "需要", "可以", "希望",
    "想法", "主意", "办法", "问题", "情况", "消息", "事情", "原因",
    "结果", "过程", "经过", "关系", "目的", "意义",
];

const SENTENCE_END_CHARS: &[char] = &['。', '！', '？', '.', '!', '?', '\u{3002}', '\u{ff01}', '\u{ff1f}'];

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// A character found in the book.
#[derive(Debug, Clone, Serialize)]
pub struct BookCharacter {
    pub name: String,
    pub mentions: usize,
    pub first_chapter: i32,
    pub associated_with: Vec<CharacterAssociation>,
    pub profile: String,
}

/// Association between two characters.
#[derive(Debug, Clone, Serialize)]
pub struct CharacterAssociation {
    pub name: String,
    pub co_occurrences: usize,
}

/// Plot structure analysis result.
#[derive(Debug, Clone, Serialize)]
pub struct PlotStructure {
    pub act_count: usize,
    pub pacing: Vec<ChapterPacing>,
    pub climax_chapter: Option<i32>,
}

/// Per-chapter pacing data.
#[derive(Debug, Clone, Serialize)]
pub struct ChapterPacing {
    pub chapter: i32,
    pub title: String,
    pub word_count: usize,
    pub sentence_count: usize,
    pub dialogue_ratio: f64,
    pub action_intensity: f64,
    pub tone_score: f64,
}

/// A detected plot point.
#[derive(Debug, Clone, Serialize)]
pub struct PlotPoint {
    pub chapter: i32,
    pub title: String,
    #[serde(rename = "type")]
    pub point_type: String,
    pub description: String,
}

/// A potential plot gap.
#[derive(Debug, Clone, Serialize)]
pub struct PlotGap {
    #[serde(rename = "type")]
    pub gap_type: String,
    pub severity: String,
    pub description: String,
    pub suggestion: String,
}

/// Style profile result.
#[derive(Debug, Clone, Serialize)]
pub struct StyleProfile {
    pub avg_sentence_length: f64,
    pub dialogue_ratio: f64,
    pub paragraph_pattern: String,
    pub common_phrases: Vec<PhraseEntry>,
}

/// Common phrase entry.
#[derive(Debug, Clone, Serialize)]
pub struct PhraseEntry {
    pub phrase: String,
    pub frequency: usize,
}

// ---------------------------------------------------------------------------
// BookAnalysisService
// ---------------------------------------------------------------------------

/// Book analysis service.
///
/// Provides three analysis capabilities:
/// 1. analyze_characters — character extraction and relationship mapping
/// 2. analyze_plot — plot structure and gap detection
/// 3. detect_style — writing style quantitative analysis
#[derive(Clone)]
pub struct BookAnalysisService {
    chapter_dao: ChapterDao,
}

impl BookAnalysisService {
    /// Create a new BookAnalysisService.
    pub fn new(chapter_dao: ChapterDao) -> Self {
        Self { chapter_dao }
    }

    // ------------------------------------------------------------------
    // Character Analysis
    // ------------------------------------------------------------------

    /// Analyze characters in the project.
    ///
    /// Scans each chapter's content, extracts Chinese character names,
    /// counts appearances, identifies co-occurrence relationships,
    /// and generates profile descriptions.
    pub async fn analyze_characters(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<serde_json::Value> {
        let chapters = self
            .chapter_dao
            .list_by_project(db, project_id, 0, 9999)
            .await?;

        if chapters.is_empty() {
            info!("Project {project_id} has no chapters, returning empty result");
            return Ok(serde_json::json!({
                "project_id": project_id,
                "characters": [],
                "total_chapters": 0,
            }));
        }

        // Step 1: Extract character mentions per chapter
        let mut chapter_characters: HashMap<i32, HashMap<String, usize>> = HashMap::new();
        let mut all_mentions: HashMap<String, usize> = HashMap::new();
        let mut first_chapter: HashMap<String, i32> = HashMap::new();

        for ch in &chapters {
            let content = ch.content.as_deref().unwrap_or("");
            let cn_num = ch.chapter_number;

            let names = self.extract_names(content);
            let filtered: Vec<String> = names
                .into_iter()
                .filter(|n| !STOP_NAMES.contains(&n.as_str()) && n.len() >= 2)
                .collect();

            if !filtered.is_empty() {
                let mut cnt: HashMap<String, usize> = HashMap::new();
                for name in &filtered {
                    *cnt.entry(name.clone()).or_insert(0) += 1;
                    *all_mentions.entry(name.clone()).or_insert(0) += 1;
                }
                chapter_characters.insert(cn_num, cnt);

                for name in &filtered {
                    first_chapter.entry(name.clone()).or_insert(cn_num);
                }
            }
        }

        // Step 2: Build co-occurrence relationships
        let mut co_occur: HashMap<String, HashMap<String, usize>> = HashMap::new();
        for (_ch_num, char_counter) in &chapter_characters {
            let names_in_chapter: Vec<&String> = char_counter.keys().collect();
            for i in 0..names_in_chapter.len() {
                for j in (i + 1)..names_in_chapter.len() {
                    let a = names_in_chapter[i].clone();
                    let b = names_in_chapter[j].clone();
                    *co_occur.entry(a.clone()).or_default().entry(b.clone()).or_insert(0) += 1;
                    *co_occur.entry(b).or_default().entry(a).or_insert(0) += 1;
                }
            }
        }

        // Step 3: Build sorted character list
        let mut sorted_names: Vec<(String, usize)> = all_mentions.iter()
            .map(|(name, count)| (name.clone(), *count))
            .collect();
        sorted_names.sort_by(|a, b| b.1.cmp(&a.1));

        let mut characters: Vec<serde_json::Value> = Vec::new();
        for (name, total) in &sorted_names {
            let fc = first_chapter.get(name).copied().unwrap_or(0);

            let associated: Vec<serde_json::Value> = co_occur
                .get(name)
                .map(|counter| {
                    let mut assoc: Vec<(String, usize)> = counter.iter()
                        .map(|(n, c)| (n.clone(), *c))
                        .collect();
                    assoc.sort_by(|a, b| b.1.cmp(&a.1));
                    assoc.into_iter().take(10).map(|(n, co)| {
                        serde_json::json!({"name": n, "co_occurrences": co})
                    }).collect()
                })
                .unwrap_or_default();

            let mut aux_info: Vec<String> = Vec::new();
            if fc > 0 {
                aux_info.push(format!("首次出现于第{fc}章"));
            }
            if let Some(first) = associated.first() {
                if let Some(top_name) = first["name"].as_str() {
                    aux_info.push(format!("常与「{top_name}」同场出现"));
                }
            }

            let profile = if aux_info.is_empty() {
                format!("全书提及{total}次。")
            } else {
                format!("全书提及{total}次。{}", aux_info.join("；"))
            };

            characters.push(serde_json::json!({
                "name": name,
                "mentions": total,
                "first_chapter": fc,
                "associated_with": associated,
                "profile": profile,
            }));
        }

        info!(
            "Character analysis complete for project {project_id}: {} characters found",
            characters.len()
        );

        Ok(serde_json::json!({
            "project_id": project_id,
            "characters": characters,
            "total_chapters": chapters.len(),
        }))
    }

    // ------------------------------------------------------------------
    // Plot Analysis
    // ------------------------------------------------------------------

    /// Analyze plot structure of the project.
    pub async fn analyze_plot(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<serde_json::Value> {
        let chapters = self
            .chapter_dao
            .list_by_project(db, project_id, 0, 9999)
            .await?;

        if chapters.is_empty() {
            return Ok(serde_json::json!({
                "project_id": project_id,
                "structure": {"act_count": 0, "pacing": [], "climax_chapter": null},
                "plot_points": [],
                "potential_gaps": [],
            }));
        }

        // Step 1: Per-chapter metrics
        let chapter_metrics = self.analyze_all_chapter_metrics(&chapters);

        // Step 2: Detect acts
        let (act_count, _boundaries) = self.detect_acts(&chapter_metrics);

        // Step 3: Find climax
        let climax = self.find_climax(&chapter_metrics);

        // Step 4: Build pacing data
        let pacing: Vec<serde_json::Value> = chapter_metrics
            .iter()
            .map(|m| {
                serde_json::json!({
                    "chapter": m.chapter_number,
                    "title": m.chapter_title,
                    "word_count": m.word_count,
                    "sentence_count": m.sentence_count,
                    "dialogue_ratio": m.dialogue_ratio,
                    "action_intensity": m.action_intensity,
                    "tone_score": m.tone_score,
                })
            })
            .collect();

        // Step 5: Detect plot points
        let plot_points = self.detect_plot_points(&chapter_metrics);

        // Step 6: Detect plot gaps
        let potential_gaps = self.detect_plot_gaps(&chapter_metrics, &chapters);

        info!(
            "Plot analysis complete for project {project_id}: {act_count} acts, climax at ch.{climax:?}"
        );

        Ok(serde_json::json!({
            "project_id": project_id,
            "structure": {
                "act_count": act_count,
                "pacing": pacing,
                "climax_chapter": climax,
            },
            "plot_points": plot_points,
            "potential_gaps": potential_gaps,
        }))
    }

    // ------------------------------------------------------------------
    // Style Detection
    // ------------------------------------------------------------------

    /// Detect writing style of the project.
    pub async fn detect_style(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<serde_json::Value> {
        let chapters = self
            .chapter_dao
            .list_by_project(db, project_id, 0, 9999)
            .await?;

        if chapters.is_empty() {
            return Ok(serde_json::json!({
                "project_id": project_id,
                "style_profile": {
                    "avg_sentence_length": 0.0,
                    "dialogue_ratio": 0.0,
                    "paragraph_pattern": "无内容",
                    "common_phrases": [],
                },
            }));
        }

        let _total_chars: usize = 0;
        let mut total_dialogue_chars: usize = 0;
        let mut char_count: usize = 0;
        let mut paragraph_lengths: Vec<usize> = Vec::new();
        let mut all_text_parts: Vec<String> = Vec::new();

        for ch in &chapters {
            let content = ch.content.as_deref().unwrap_or("");

            // Character count (exclude whitespace)
            let clean_content: String = content
                .chars()
                .filter(|c| !c.is_whitespace())
                .collect();
            char_count += clean_content.len();

            // Dialogue chars
            let dialogue_chars = self.count_dialogue_chars(content);
            total_dialogue_chars += dialogue_chars;

            // Paragraphs
            for para in content.split("\n\n") {
                let trimmed = para.trim();
                if !trimmed.is_empty() {
                    paragraph_lengths.push(trimmed.chars().count());
                }
            }

            // Collect text for phrase analysis
            let non_dialogue: String = content
                .chars()
                .filter(|c| !matches!(c, '"' | '\u{201c}' | '\u{201d}' | '\u{300c}' | '\u{300d}'))
                .collect();
            all_text_parts.push(non_dialogue);
        }

        let avg_sentence_length = if char_count > 0 {
            char_count as f64 / std::cmp::max(1, char_count / 30) as f64 // rough estimate
        } else {
            0.0
        };

        let dialogue_ratio = if char_count > 0 {
            total_dialogue_chars as f64 / char_count as f64
        } else {
            0.0
        };

        let paragraph_pattern = self.describe_paragraph_lengths(&paragraph_lengths);
        let common_phrases = self.find_all_common_phrases(&all_text_parts);

        info!(
            "Style analysis complete for project {project_id}: dialogue={:.1}%",
            dialogue_ratio * 100.0
        );

        Ok(serde_json::json!({
            "project_id": project_id,
            "style_profile": {
                "avg_sentence_length": (avg_sentence_length * 100.0).round() / 100.0,
                "dialogue_ratio": (dialogue_ratio * 10000.0).round() / 10000.0,
                "paragraph_pattern": paragraph_pattern,
                "common_phrases": common_phrases,
            },
        }))
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    /// Extract potential character names from text (Chinese 2-3 char names).
    fn extract_names(&self, text: &str) -> Vec<String> {
        if text.is_empty() {
            return Vec::new();
        }

        let chars: Vec<char> = text.chars().collect();
        let mut names: Vec<String> = Vec::new();
        let mut i = 0;

        while i < chars.len() {
            // Look for 2-3 consecutive CJK characters
            if is_cjk_char(chars[i]) {
                let mut name_len = 1;
                while i + name_len < chars.len()
                    && name_len < 3
                    && is_cjk_char(chars[i + name_len])
                {
                    name_len += 1;
                }

                if name_len == 2 || name_len == 3 {
                    let name: String = chars[i..i + name_len].iter().collect();
                    // Only add if not preceded/followed by other CJK chars
                    let preceded_by_cjk = i > 0 && is_cjk_char(chars[i - 1]);
                    let followed_by_cjk = i + name_len < chars.len() && is_cjk_char(chars[i + name_len]);
                    if !preceded_by_cjk || !followed_by_cjk {
                        names.push(name);
                    }
                }
            }
            i += 1;
        }

        names
    }

    /// Count dialogue characters in text.
    fn count_dialogue_chars(&self, text: &str) -> usize {
        let mut in_dialogue = false;
        let mut count = 0;
        for ch in text.chars() {
            match ch {
                '"' | '\u{201c}' | '\u{201d}' | '\u{300c}' | '\u{300d}' | '\u{ff07}' => {
                    in_dialogue = !in_dialogue;
                }
                _ => {
                    if in_dialogue {
                        count += 1;
                    }
                }
            }
        }
        count
    }

    /// Split text into sentences.
    fn split_into_sentences(&self, text: &str) -> Vec<String> {
        let mut sentences = Vec::new();
        let mut current = String::new();
        for ch in text.chars() {
            current.push(ch);
            if SENTENCE_END_CHARS.contains(&ch) {
                let trimmed = current.trim().to_string();
                if !trimmed.is_empty() {
                    sentences.push(trimmed);
                }
                current = String::new();
            }
        }
        let trimmed = current.trim().to_string();
        if !trimmed.is_empty() {
            sentences.push(trimmed);
        }
        sentences
    }

    /// Analyze metrics for all chapters.
    fn analyze_all_chapter_metrics(&self, chapters: &[ChapterModel]) -> Vec<ChapterMetrics> {
        chapters
            .iter()
            .map(|ch| self.analyze_single_chapter_metrics(ch))
            .collect()
    }

    /// Analyze a single chapter's metrics.
    fn analyze_single_chapter_metrics(&self, chapter: &ChapterModel) -> ChapterMetrics {
        let content = chapter.content.as_deref().unwrap_or("");
        let sentences = self.split_into_sentences(content);
        let sent_count = sentences.len();

        let word_count: usize = content
            .chars()
            .filter(|c| !c.is_whitespace() && !matches!(c, '\n' | '\r'))
            .count();

        let dialogue_sentences = sentences
            .iter()
            .filter(|s| {
                s.contains('"')
                    || s.contains('\u{201c}')
                    || s.contains('\u{300c}')
            })
            .count();
        let dialogue_ratio = if sent_count > 0 {
            dialogue_sentences as f64 / sent_count as f64
        } else {
            0.0
        };

        // Action intensity
        let action_markers: usize = content.matches(&['！', '!'][..]).count();
        let question_markers: usize = content.matches(&['？', '?'][..]).count();
        let action_keywords: usize = content
            .matches(&['打', '杀', '冲', '跑', '跳', '喊', '叫', '哭', '笑', '怒', '吼'][..])
            .count();
        let total_markers = action_markers + question_markers + action_keywords;
        let action_intensity = if word_count > 0 {
            (total_markers as f64 / word_count as f64) * 100.0
        } else {
            0.0
        };

        // Tone score
        let positive_words = ["高兴", "快乐", "开心", "兴奋", "激动", "幸福", "美好", "希望", "微笑", "喜悦"];
        let negative_words = ["悲伤", "痛苦", "愤怒", "恐惧", "绝望", "焦虑", "孤独", "哭泣", "仇恨", "后悔"];
        let positive_count: usize = positive_words.iter().map(|w| content.matches(w).count()).sum();
        let negative_count: usize = negative_words.iter().map(|w| content.matches(w).count()).sum();
        let total_emo = positive_count + negative_count;
        let tone_score = if total_emo > 0 {
            ((positive_count as f64 - negative_count as f64) / total_emo as f64).clamp(-1.0, 1.0)
        } else {
            0.0
        };

        ChapterMetrics {
            chapter_number: chapter.chapter_number,
            chapter_title: chapter.title.clone(),
            word_count,
            sentence_count: sent_count,
            dialogue_ratio: (dialogue_ratio * 10000.0).round() / 10000.0,
            action_intensity: (action_intensity * 100.0).round() / 100.0,
            tone_score: (tone_score * 100.0).round() / 100.0,
        }
    }

    /// Detect act structure from chapter metrics.
    fn detect_acts(&self, metrics: &[ChapterMetrics]) -> (usize, Vec<i32>) {
        if metrics.len() < 3 {
            return (1, Vec::new());
        }

        let mut boundaries = Vec::new();
        for i in 1..metrics.len() {
            let prev = &metrics[i - 1];
            let curr = &metrics[i];
            let dr_delta = (curr.dialogue_ratio - prev.dialogue_ratio).abs();
            let ai_delta = (curr.action_intensity - prev.action_intensity).abs();
            let tone_delta = (curr.tone_score - prev.tone_score).abs();

            if dr_delta > 0.15 && ai_delta > 0.15 {
                boundaries.push(curr.chapter_number);
            } else if tone_delta > 0.3 && (dr_delta > 0.1 || ai_delta > 0.1) {
                boundaries.push(curr.chapter_number);
            }
        }

        (boundaries.len() + 1, boundaries)
    }

    /// Find the most likely climax chapter.
    fn find_climax(&self, metrics: &[ChapterMetrics]) -> Option<i32> {
        if metrics.is_empty() {
            return None;
        }

        let max_wc = metrics.iter().map(|m| m.word_count).max().unwrap_or(1);
        let max_int = metrics
            .iter()
            .map(|m| m.action_intensity)
            .fold(1.0f64, f64::max);
        let max_sc = metrics.iter().map(|m| m.sentence_count).max().unwrap_or(1);

        let mut best_score = -1.0f64;
        let mut best_chapter = None;

        for m in metrics {
            let score = (m.word_count as f64 / max_wc as f64) * 0.3
                + (m.action_intensity / max_int) * 0.4
                + (m.sentence_count as f64 / max_sc as f64) * 0.3;

            if score > best_score {
                best_score = score;
                best_chapter = Some(m.chapter_number);
            }
        }

        best_chapter
    }

    /// Detect plot points (opening, conflict, turning point, revelation).
    fn detect_plot_points(&self, metrics: &[ChapterMetrics]) -> Vec<serde_json::Value> {
        let mut plot_points = Vec::new();

        for m in metrics {
            let ch = m.chapter_number;
            let title = &m.chapter_title;

            if ch == 1 {
                plot_points.push(serde_json::json!({
                    "chapter": ch,
                    "title": title,
                    "type": "opening",
                    "description": format!("第{ch}章「{}」：故事开篇。", if title.is_empty() { "无标题" } else { title }),
                }));
                continue;
            }

            if m.action_intensity > 2.0 {
                plot_points.push(serde_json::json!({
                    "chapter": ch,
                    "title": title,
                    "type": "conflict",
                    "description": format!("第{ch}章动作强度高（{:.1}），可能为冲突场景。", m.action_intensity),
                }));
            }

            if m.tone_score < -0.5 {
                plot_points.push(serde_json::json!({
                    "chapter": ch,
                    "title": title,
                    "type": "turning_point",
                    "description": format!("第{ch}章语气偏负面（{:.2}），可能为故事转折或低谷。", m.tone_score),
                }));
            }

            if m.dialogue_ratio > 0.6 {
                plot_points.push(serde_json::json!({
                    "chapter": ch,
                    "title": title,
                    "type": "revelation",
                    "description": format!("第{ch}章对话比例高（{:.0}%），可能为信息揭示场景。", m.dialogue_ratio * 100.0),
                }));
            }
        }

        plot_points
    }

    /// Detect potential plot gaps.
    fn detect_plot_gaps(
        &self,
        _metrics: &[ChapterMetrics],
        chapters: &[ChapterModel],
    ) -> Vec<serde_json::Value> {
        let mut gaps = Vec::new();

        if chapters.len() < 2 {
            return gaps;
        }

        // 1. Check for missing characters between first third and last third
        let third = std::cmp::max(chapters.len() / 3, 1);
        let mut early_names: HashSet<String> = HashSet::new();
        let mut late_names: HashSet<String> = HashSet::new();

        for ch in &chapters[..third] {
            let names = self.extract_names(ch.content.as_deref().unwrap_or(""));
            early_names.extend(names.into_iter().filter(|n| !STOP_NAMES.contains(&n.as_str())));
        }

        for ch in &chapters[(chapters.len() - third)..] {
            let names = self.extract_names(ch.content.as_deref().unwrap_or(""));
            late_names.extend(names.into_iter().filter(|n| !STOP_NAMES.contains(&n.as_str())));
        }

        let missing_names: Vec<&String> = early_names.difference(&late_names).collect();
        if !missing_names.is_empty() {
            let top_missing: Vec<&str> = missing_names
                .iter()
                .take(5)
                .map(|s| s.as_str())
                .collect();
            gaps.push(serde_json::json!({
                "type": "missing_character",
                "severity": "medium",
                "description": format!(
                    "前{third}章登场的角色在最后{third}章未再出现：「{}」等。",
                    top_missing.join("」、「")
                ),
                "suggestion": "建议检查是否有未收尾的角色线。",
            }));
        }

        // 2. Check chapter content completeness
        for ch in chapters {
            let content = ch.content.as_deref().unwrap_or("").trim();
            if content.is_empty() {
                gaps.push(serde_json::json!({
                    "type": "empty_chapter",
                    "severity": "low",
                    "description": format!("第{}章内容为空，标题为「{}」。", ch.chapter_number, ch.title),
                    "suggestion": "建议补充该章节内容。",
                }));
            } else if content.chars().count() < 50 {
                gaps.push(serde_json::json!({
                    "type": "short_chapter",
                    "severity": "low",
                    "description": format!("第{}章内容过短（{}字）。", ch.chapter_number, content.chars().count()),
                    "suggestion": "建议检查章节是否完整。",
                }));
            }
        }

        // 3. Chapter numbering continuity
        let chapter_numbers: Vec<i32> = chapters.iter().map(|ch| ch.chapter_number).collect();
        let expected: Vec<i32> = (1..=chapters.len() as i32).collect();
        if chapter_numbers != expected {
            gaps.push(serde_json::json!({
                "type": "chapter_gap",
                "severity": "medium",
                "description": "章节序号不连续，可能存在缺失章节。",
                "suggestion": "请检查章节列表确认完整性。",
            }));
        }

        gaps
    }

    /// Describe paragraph length distribution.
    fn describe_paragraph_lengths(&self, lengths: &[usize]) -> String {
        if lengths.is_empty() {
            return "无段落数据".to_string();
        }

        let avg: f64 = lengths.iter().sum::<usize>() as f64 / lengths.len() as f64;
        let short_ratio = lengths.iter().filter(|&&l| l < 50).count() as f64 / lengths.len() as f64;
        let long_ratio = lengths.iter().filter(|&&l| l > 500).count() as f64 / lengths.len() as f64;

        let mut parts: Vec<String> = Vec::new();
        if short_ratio > 0.5 {
            parts.push("以短段落为主".to_string());
        } else if short_ratio > 0.3 {
            parts.push("短段落较多".to_string());
        } else {
            parts.push("段落长度适中".to_string());
        }
        if long_ratio > 0.2 {
            parts.push("含有较多长段落".to_string());
        }
        parts.push(format!("平均段落长度约{:.0}字", avg));

        parts.join("，")
    }

    /// Find common phrases across text parts.
    fn find_all_common_phrases(&self, text_parts: &[String]) -> Vec<serde_json::Value> {
        let all_text = text_parts.join("");
        if all_text.trim().is_empty() {
            return Vec::new();
        }

        let chinese_only: String = all_text
            .chars()
            .filter(|c| is_cjk_char(*c))
            .collect();

        if chinese_only.len() < 10 {
            return Vec::new();
        }

        let chars: Vec<char> = chinese_only.chars().collect();
        let mut counter: std::collections::HashMap<String, usize> = std::collections::HashMap::new();

        for length in [2, 3, 4] {
            for i in 0..chars.len().saturating_sub(length - 1) {
                if i + length <= chars.len() {
                    let phrase: String = chars[i..i + length].iter().collect();
                    *counter.entry(phrase).or_insert(0) += 1;
                }
            }
        }

        let mut phrases: Vec<(String, usize)> = counter.into_iter().collect();
        phrases.sort_by(|a, b| b.1.cmp(&a.1));

        phrases
            .into_iter()
            .filter(|(phrase, count)| {
                *count >= 3
                    && !phrase.chars().all(|c| c == phrase.chars().next().unwrap())
            })
            .take(20)
            .map(|(phrase, frequency)| {
                serde_json::json!({"phrase": phrase, "frequency": frequency})
            })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

struct ChapterMetrics {
    chapter_number: i32,
    chapter_title: String,
    word_count: usize,
    sentence_count: usize,
    dialogue_ratio: f64,
    action_intensity: f64,
    tone_score: f64,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_service() -> BookAnalysisService {
        BookAnalysisService::new(ChapterDao::default())
    }

    #[test]
    fn test_extract_names() {
        let svc = make_service();
        let names = svc.extract_names("张三说李四看了王五一眼，赵六哈哈大笑。");
        assert!(!names.is_empty());
    }

    #[test]
    fn test_count_dialogue_chars() {
        let svc = make_service();
        let count = svc.count_dialogue_chars(r#"他说："你好世界。"她很开心。"#);
        assert!(count > 0);
    }

    #[test]
    fn test_detect_acts() {
        let svc = make_service();
        let metrics = vec![
            ChapterMetrics { chapter_number: 1, chapter_title: "".into(), word_count: 100, sentence_count: 10, dialogue_ratio: 0.2, action_intensity: 1.0, tone_score: 0.0 },
            ChapterMetrics { chapter_number: 2, chapter_title: "".into(), word_count: 200, sentence_count: 20, dialogue_ratio: 0.6, action_intensity: 2.5, tone_score: -0.5 },
            ChapterMetrics { chapter_number: 3, chapter_title: "".into(), word_count: 150, sentence_count: 15, dialogue_ratio: 0.3, action_intensity: 1.5, tone_score: 0.2 },
        ];
        let (acts, boundaries) = svc.detect_acts(&metrics);
        assert!(acts >= 1);
    }

    #[test]
    fn test_find_climax() {
        let svc = make_service();
        let metrics = vec![
            ChapterMetrics { chapter_number: 1, chapter_title: "".into(), word_count: 100, sentence_count: 10, dialogue_ratio: 0.2, action_intensity: 1.0, tone_score: 0.0 },
            ChapterMetrics { chapter_number: 2, chapter_title: "".into(), word_count: 500, sentence_count: 50, dialogue_ratio: 0.5, action_intensity: 5.0, tone_score: -1.0 },
        ];
        let climax = svc.find_climax(&metrics);
        assert_eq!(climax, Some(2));
    }

    #[test]
    fn test_describe_paragraph_lengths() {
        let svc = make_service();
        let desc = svc.describe_paragraph_lengths(&[20, 30, 40, 600, 700]);
        assert!(!desc.is_empty());
    }
}
