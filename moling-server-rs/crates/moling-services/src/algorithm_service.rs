//! 墨灵 (Moling) — Algorithm Service (通用算法).
//!
//! Implements text analysis algorithms:
//! - Sentence analysis (sentence count, dialogue ratio, paragraph pattern)
//! - Style fingerprint extraction
//! - Statistical calculations
//!
//! Ported from Python `app/service/algorithm_service.py`.

use serde::Serialize;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// Sentence analysis result.
#[derive(Debug, Clone, Serialize)]
pub struct SentenceAnalysis {
    /// Total sentence count.
    pub sentence_count: usize,
    /// Average sentence length in characters.
    pub avg_sentence_length: f64,
    /// Long sentence count (> 30 chars).
    pub long_sentence_count: usize,
    /// Short sentence count (< 10 chars).
    pub short_sentence_count: usize,
}

/// Dialogue analysis result.
#[derive(Debug, Clone, Serialize)]
pub struct DialogueAnalysis {
    /// Dialogue ratio (0.0–1.0).
    pub dialogue_ratio: f64,
    /// Dialogue sentence count.
    pub dialogue_sentence_count: usize,
    /// Narrative sentence count.
    pub narrative_sentence_count: usize,
}

/// Paragraph analysis result.
#[derive(Debug, Clone, Serialize)]
pub struct ParagraphAnalysis {
    /// Paragraph count.
    pub paragraph_count: usize,
    /// Average paragraph length in characters.
    pub avg_paragraph_length: f64,
    /// Short paragraph ratio (< 50 chars).
    pub short_paragraph_ratio: f64,
    /// Long paragraph ratio (> 500 chars).
    pub long_paragraph_ratio: f64,
    /// Paragraph pattern description.
    pub pattern: String,
}

/// Style fingerprint extracted from text.
#[derive(Debug, Clone, Serialize)]
pub struct StyleFingerprint {
    /// Average sentence length in characters.
    pub avg_sentence_length: f64,
    /// Dialogue ratio (0.0–1.0).
    pub dialogue_ratio: f64,
    /// Dominant point of view.
    pub dominant_pov: String,
    /// Average paragraph length.
    pub avg_paragraph_length: f64,
    /// Exclamation mark density (per 1000 chars).
    pub exclamation_density: f64,
    /// Common phrases found.
    pub common_phrases: Vec<PhraseFrequency>,
}

/// A frequent phrase with its count.
#[derive(Debug, Clone, Serialize)]
pub struct PhraseFrequency {
    pub phrase: String,
    pub frequency: usize,
}

// ---------------------------------------------------------------------------
// AlgorithmService
// ---------------------------------------------------------------------------

/// Service for text analysis algorithms.
///
/// Pure computation — no database or LLM calls.
#[derive(Clone)]
pub struct AlgorithmService;

impl AlgorithmService {
    /// Create a new AlgorithmService.
    pub fn new() -> Self {
        Self
    }

    // ------------------------------------------------------------------
    // Sentence Analysis
    // ------------------------------------------------------------------

    /// Analyze sentence structure of the given text.
    ///
    /// Returns sentence count, average length, and long/short sentence counts.
    pub fn analyze_sentences(&self, text: &str) -> SentenceAnalysis {
        let sentences = self.split_sentences(text);
        let sentence_count = sentences.len();

        let total_chars: usize = sentences.iter().map(|s| s.chars().count()).sum();
        let avg_sentence_length = if sentence_count > 0 {
            total_chars as f64 / sentence_count as f64
        } else {
            0.0
        };

        let long_sentence_count = sentences
            .iter()
            .filter(|s| s.chars().count() > 30)
            .count();
        let short_sentence_count = sentences
            .iter()
            .filter(|s| s.chars().count() < 10)
            .count();

        SentenceAnalysis {
            sentence_count,
            avg_sentence_length: (avg_sentence_length * 100.0).round() / 100.0,
            long_sentence_count,
            short_sentence_count,
        }
    }

    /// Split text into sentences using Chinese/English sentence-ending punctuation.
    pub fn split_sentences(&self, text: &str) -> Vec<String> {
        let mut sentences: Vec<String> = Vec::new();
        let mut current = String::new();

        for ch in text.chars() {
            current.push(ch);
            if matches!(ch, '。' | '！' | '？' | '!' | '?' | '\n') {
                let trimmed = current.trim().to_string();
                if !trimmed.is_empty() {
                    sentences.push(trimmed);
                }
                current = String::new();
            }
        }

        // Don't forget the last segment
        let trimmed = current.trim().to_string();
        if !trimmed.is_empty() {
            sentences.push(trimmed);
        }

        sentences
    }

    // ------------------------------------------------------------------
    // Dialogue Analysis
    // ------------------------------------------------------------------

    /// Analyze dialogue proportion in text.
    ///
    /// Uses quotation marks as dialogue delimiters.
    pub fn analyze_dialogue(&self, text: &str) -> DialogueAnalysis {
        let sentences = self.split_sentences(text);
        let dialogue_quotes = ['"', '\u{201c}', '\u{201d}', '\u{300c}', '\u{300d}', '\u{300e}', '\u{300f}'];

        let dialogue_sentence_count = sentences
            .iter()
            .filter(|s| s.chars().any(|c| dialogue_quotes.contains(&c)))
            .count();

        let narrative_sentence_count = sentences.len() - dialogue_sentence_count;
        let dialogue_ratio = if !sentences.is_empty() {
            dialogue_sentence_count as f64 / sentences.len() as f64
        } else {
            0.0
        };

        DialogueAnalysis {
            dialogue_ratio: (dialogue_ratio * 10000.0).round() / 10000.0,
            dialogue_sentence_count,
            narrative_sentence_count,
        }
    }

    // ------------------------------------------------------------------
    // Paragraph Analysis
    // ------------------------------------------------------------------

    /// Analyze paragraph structure in text.
    pub fn analyze_paragraphs(&self, text: &str) -> ParagraphAnalysis {
        let paragraphs: Vec<&str> = text
            .split("\n\n")
            .map(|p| p.trim())
            .filter(|p| !p.is_empty())
            .collect();

        let paragraph_count = paragraphs.len();

        let total_chars: usize = paragraphs.iter().map(|p| p.chars().count()).sum();
        let avg_paragraph_length = if paragraph_count > 0 {
            total_chars as f64 / paragraph_count as f64
        } else {
            0.0
        };

        let short_count = paragraphs.iter().filter(|p| p.chars().count() < 50).count();
        let long_count = paragraphs.iter().filter(|p| p.chars().count() > 500).count();

        let short_paragraph_ratio = if paragraph_count > 0 {
            short_count as f64 / paragraph_count as f64
        } else {
            0.0
        };

        let long_paragraph_ratio = if paragraph_count > 0 {
            long_count as f64 / paragraph_count as f64
        } else {
            0.0
        };

        let pattern = if short_paragraph_ratio > 0.5 {
            "以短段落为主".to_string()
        } else if short_paragraph_ratio > 0.3 {
            "短段落较多".to_string()
        } else {
            "段落长度适中".to_string()
        };

        ParagraphAnalysis {
            paragraph_count,
            avg_paragraph_length: (avg_paragraph_length * 100.0).round() / 100.0,
            short_paragraph_ratio: (short_paragraph_ratio * 10000.0).round() / 10000.0,
            long_paragraph_ratio: (long_paragraph_ratio * 10000.0).round() / 10000.0,
            pattern,
        }
    }

    // ------------------------------------------------------------------
    // Style Fingerprint
    // ------------------------------------------------------------------

    /// Extract style fingerprint from text.
    ///
    /// Computes sentence length, dialogue ratio, POV detection, paragraph length,
    /// and exclamation density.
    pub fn extract_style_fingerprint(&self, text: &str) -> StyleFingerprint {
        let sentence_analysis = self.analyze_sentences(text);
        let dialogue_analysis = self.analyze_dialogue(text);
        let paragraph_analysis = self.analyze_paragraphs(text);

        let dominant_pov = self.detect_pov(text);

        let excl_count = text.chars().filter(|c| *c == '！' || *c == '!').count();
        let total_chars = text.chars().count();
        let exclamation_density = if total_chars > 0 {
            (excl_count as f64) / (total_chars as f64) * 1000.0
        } else {
            0.0
        };

        let common_phrases = self.find_common_phrases(text, 3);

        StyleFingerprint {
            avg_sentence_length: sentence_analysis.avg_sentence_length,
            dialogue_ratio: dialogue_analysis.dialogue_ratio,
            dominant_pov,
            avg_paragraph_length: paragraph_analysis.avg_paragraph_length,
            exclamation_density: (exclamation_density * 100.0).round() / 100.0,
            common_phrases,
        }
    }

    /// Detect dominant point of view (first/second/third person).
    pub fn detect_pov(&self, text: &str) -> String {
        let first_count = text.matches('我').count();
        let third_count = text.matches('他').count() + text.matches('她').count();

        if first_count > third_count {
            "first".to_string()
        } else {
            "third".to_string()
        }
    }

    // ------------------------------------------------------------------
    // Common Phrases
    // ------------------------------------------------------------------

    /// Find frequently occurring phrases (2-4 character combinations).
    pub fn find_common_phrases(&self, text: &str, min_freq: usize) -> Vec<PhraseFrequency> {
        // Extract continuous Chinese characters
        let chinese_only: String = text
            .chars()
            .filter(|c| matches!(c, '\u{4e00}'..='\u{9fff}'))
            .collect();

        if chinese_only.len() < 10 {
            return Vec::new();
        }

        let chars: Vec<char> = chinese_only.chars().collect();
        let mut phrase_counter: std::collections::HashMap<String, usize> =
            std::collections::HashMap::new();

        // Count 2-4 character phrases
        for length in [2, 3, 4] {
            for i in 0..chars.len().saturating_sub(length - 1) {
                if i + length <= chars.len() {
                    let phrase: String = chars[i..i + length].iter().collect();
                    *phrase_counter.entry(phrase).or_insert(0) += 1;
                }
            }
        }

        let mut phrases: Vec<(String, usize)> = phrase_counter.into_iter().collect();
        phrases.sort_by(|a, b| b.1.cmp(&a.1));

        phrases
            .into_iter()
            .filter(|(phrase, count)| {
                *count >= min_freq
                    && phrase.chars().next().is_some_and(|first| !phrase.chars().all(|c| c == first))
            })
            .take(20)
            .map(|(phrase, frequency)| PhraseFrequency { phrase, frequency })
            .collect()
    }

    // ------------------------------------------------------------------
    // Statistics
    // ------------------------------------------------------------------

    /// Calculate text word count (Chinese characters).
    pub fn word_count(&self, text: &str) -> usize {
        text.chars()
            .filter(|c| !c.is_whitespace() && !matches!(c, '\n' | '\r'))
            .count()
    }

    /// Calculate action intensity score (per 100 chars).
    pub fn action_intensity(&self, text: &str) -> f64 {
        let total = self.word_count(text) as f64;
        if total == 0.0 {
            return 0.0;
        }

        let action_keywords = ["打", "杀", "冲", "跑", "跳", "喊", "叫", "哭", "笑", "怒", "吼"];
        let action_count: usize = action_keywords
            .iter()
            .map(|kw| text.matches(kw).count())
            .sum();

        let excl_count = text.matches('！').count() + text.matches('!').count();
        let question_count = text.matches('？').count() + text.matches('?').count();

        let total_markers = action_count + excl_count + question_count;
        ((total_markers as f64 / total) * 100.0 * 100.0).round() / 100.0
    }

    /// Calculate tone score (-1.0 to 1.0) based on positive/negative word ratios.
    pub fn tone_score(&self, text: &str) -> f64 {
        let positive_words = [
            "高兴", "快乐", "开心", "兴奋", "激动", "幸福", "美好", "希望", "微笑", "喜悦",
        ];
        let negative_words = [
            "悲伤", "痛苦", "愤怒", "恐惧", "绝望", "焦虑", "孤独", "哭泣", "仇恨", "后悔",
        ];

        let positive_count: usize = positive_words.iter().map(|w| text.matches(w).count()).sum();
        let negative_count: usize = negative_words.iter().map(|w| text.matches(w).count()).sum();
        let total = positive_count + negative_count;

        if total == 0 {
            return 0.0;
        }

        let ratio = (positive_count as f64 - negative_count as f64) / total as f64;
        (ratio * 100.0).round() / 100.0
    }

    /// Calculate chapter metrics combining all dimensions.
    pub fn chapter_metrics(&self, text: &str) -> serde_json::Value {
        let sa = self.analyze_sentences(text);
        let da = self.analyze_dialogue(text);
        let pa = self.analyze_paragraphs(text);

        serde_json::json!({
            "word_count": self.word_count(text),
            "sentence_count": sa.sentence_count,
            "avg_sentence_length": sa.avg_sentence_length,
            "dialogue_ratio": da.dialogue_ratio,
            "paragraph_count": pa.paragraph_count,
            "avg_paragraph_length": pa.avg_paragraph_length,
            "action_intensity": self.action_intensity(text),
            "tone_score": self.tone_score(text),
        })
    }
}

impl Default for AlgorithmService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_split_sentences() {
        let svc = AlgorithmService::new();
        let sentences = svc.split_sentences("第一句话。第二句话！第三句话？");
        assert_eq!(sentences.len(), 3);
        assert!(sentences[0].contains("第一句话"));
    }

    #[test]
    fn test_word_count() {
        let svc = AlgorithmService::new();
        let count = svc.word_count("这是一段测试文本。");
        assert_eq!(count, 9);
    }

    #[test]
    fn test_detect_pov() {
        let svc = AlgorithmService::new();
        let pov = svc.detect_pov("我走在路上。我看到了一个人。");
        assert_eq!(pov, "first");
        let pov = svc.detect_pov("他走在路上。她看到了他。");
        assert_eq!(pov, "third");
    }

    #[test]
    fn test_action_intensity() {
        let svc = AlgorithmService::new();
        let intensity = svc.action_intensity("打杀冲跑跳喊叫哭笑哭笑怒吼！？");
        assert!(intensity > 0.0);
    }

    #[test]
    fn test_tone_score() {
        let svc = AlgorithmService::new();
        let score = svc.tone_score("今天非常高兴快乐开心幸福。");
        assert!(score > 0.0);
    }

    #[test]
    fn test_analyze_dialogue() {
        let svc = AlgorithmService::new();
        let da = svc.analyze_dialogue(r#"他说："你好。"她回答："你好。"叙述部分。"#);
        assert!(da.dialogue_ratio > 0.0);
    }

    #[test]
    fn test_find_common_phrases() {
        let svc = AlgorithmService::new();
        let phrases = svc.find_common_phrases(
            "他看着他看着他看着他看着他看着他看着他看着他",
            3,
        );
        assert!(!phrases.is_empty());
    }

    #[test]
    fn test_chapter_metrics() {
        let svc = AlgorithmService::new();
        let metrics = svc.chapter_metrics("测试文本。第二句！第三句？");
        let wc = metrics["word_count"].as_u64().unwrap();
        assert!(wc > 0);
    }
}
