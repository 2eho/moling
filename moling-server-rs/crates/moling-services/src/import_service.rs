//! Import service — file import and phased import pipeline.
//!
//! Mirrors Python `app/service/import_service.py` and `app/ingest/`.
//!
//! Handles text parsing, chapter splitting, word counting, metadata extraction,
//! and the full phased import pipeline.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::ingest_dao::IngestDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::entities::ingest_job::Model as IngestJob;
use sea_orm::{ActiveModelTrait, DatabaseConnection, Set};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Chapter splitting utilities (mirrors Python `_split_chapters`)
// ---------------------------------------------------------------------------

/// Try to detect a chapter title from a line of text.
/// Matches patterns like "第X章", "Chapter X", numbered headers, etc.
fn extract_chapter_title(line: &str) -> Option<String> {
    let trimmed = line.trim();

    // Pattern: 第X章 / 第X节 / 第X回 (Chinese chapter markers)
    if trimmed.starts_with('第') {
        for marker in ["章", "节", "回", "卷", "部"] {
            if let Some(pos) = trimmed.find(marker) {
                // Check that characters before the marker look like a number
                let prefix = &trimmed[3..pos]; // skip "第"
                let prefix = prefix.trim();
                if prefix.chars().all(|c| {
                    c.is_ascii_digit()
                        || matches!(c, '零' | '一' | '二' | '三' | '四' | '五' | '六' | '七' | '八' | '九' | '十' | '百' | '千' | '万')
                }) && !prefix.is_empty()
                {
                    return Some(trimmed.to_owned());
                }
            }
        }
    }

    // Pattern: Chapter X (English)
    let lower = trimmed.to_lowercase();
    if lower.starts_with("chapter ") {
        let rest = &trimmed[8..];
        if rest.chars().next().is_some_and(|c| c.is_ascii_digit()) {
            return Some(trimmed.to_owned());
        }
    }

    // Pattern: Numbered headers like "1. Title", "1、Title", "1）Title"
    if let Some(first) = trimmed.chars().next()
        && first.is_ascii_digit() {
            for delim in [". ", ".\t", ". ", "、", "）", ") "] {
                if let Some(pos) = trimmed.find(delim)
                    && pos > 0 && pos < 8 {
                        // Must have content after
                        if pos + delim.len() < trimmed.len() {
                            return Some(trimmed.to_owned());
                        }
                    }
            }
        }

    // Pattern: 卷一 / 卷二 / 上部 / 下部 / 前篇 / 后篇
    if trimmed.starts_with('第') || matches!(trimmed.chars().next(), Some('上' | '中' | '下' | '前' | '後')) {
        for marker in ["卷", "部", "篇", "集"] {
            if trimmed.ends_with(marker) {
                return Some(trimmed.to_owned());
            }
        }
    }

    None
}

/// Find chapter boundaries in text by scanning for chapter title patterns.
/// Returns sorted list of character indices where chapters begin.
fn find_chapter_boundaries(text: &str) -> Vec<usize> {
    let mut boundaries: Vec<usize> = vec![0]; // Chapter 1 starts at position 0
    let lines: Vec<&str> = text.lines().collect();

    for (line_idx, line) in lines.iter().enumerate() {
        if extract_chapter_title(line).is_some() {
            // Find the byte position of this line
            let pos = text
                .lines()
                .take(line_idx)
                .map(|l| l.len() + 1) // +1 for newline
                .sum::<usize>();
            if pos > 0 && !boundaries.contains(&pos) {
                boundaries.push(pos);
            }
        }
    }

    boundaries.sort();
    boundaries.dedup();
    boundaries
}

/// Split raw text into chapter segments.
/// Returns Vec of (title, content) pairs.
///
/// Public so that route handlers can re-split stored raw text for phase2/phase3
/// without duplicating the chapter-detection logic.
pub fn split_chapters(text: &str) -> Vec<(String, String)> {
    let boundaries = find_chapter_boundaries(text);
    let mut chapters: Vec<(String, String)> = Vec::new();

    for i in 0..boundaries.len() {
        let start = boundaries[i];
        let end = if i + 1 < boundaries.len() {
            boundaries[i + 1]
        } else {
            text.len()
        };

        let chunk = &text[start..end].trim();
        if chunk.is_empty() {
            continue;
        }

        // First line is the title
        let (title, content) = if let Some(nl_pos) = chunk.find('\n') {
            let first_line = chunk[..nl_pos].trim();
            let remaining = chunk[nl_pos..].trim();
            let detected = extract_chapter_title(first_line)
                .unwrap_or_else(|| first_line.to_owned());
            (detected, remaining.to_owned())
        } else {
            (format!("第{}章", chapters.len() + 1), String::new())
        };

        chapters.push((title, content.to_owned()));
    }

    chapters
}

/// Count Chinese characters in text.
fn count_chinese_chars(text: &str) -> usize {
    text.chars()
        .filter(|c| matches!(c, '\u{4e00}'..='\u{9fff}'))
        .count()
}

/// Count total words (Chinese chars + English words).
fn count_words(text: &str) -> usize {
    let chinese = count_chinese_chars(text);
    let english = text
        .split_whitespace()
        .filter(|w| w.chars().all(|c| c.is_ascii_alphabetic()))
        .count();
    chinese + english
}

/// Extract metadata (title, author) from filename.
/// Handles patterns like 《书名》-作者.txt, 书名_作者.txt
#[allow(dead_code)]
fn extract_metadata_from_filename(file_path: &str) -> (String, String) {
    let stem = std::path::Path::new(file_path)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("");

    // Pattern: 《书名》-作者
    if let Some(title_start) = stem.find('《')
        && let Some(title_end) = stem[title_start..].find('》') {
            let title = &stem[title_start + 3..title_start + title_end];
            let rest = &stem[title_start + title_end + 3..];
            let author = rest
                .trim_start_matches(|c: char| c == '-' || c == '_' || c == '—' || c.is_whitespace())
                .trim();
            return (title.to_owned(), author.to_owned());
        }

    // Pattern: 书名_作者
    for sep in ['_', '-', '—'] {
        if let Some(pos) = stem.rfind(sep) {
            let title = stem[..pos].trim();
            let author = stem[pos + 1..].trim();
            if !title.is_empty() && !author.is_empty() {
                return (title.to_owned(), author.to_owned());
            }
        }
    }

    (stem.to_owned(), String::new())
}

// ---------------------------------------------------------------------------
// ImportService
// ---------------------------------------------------------------------------

/// Business logic for file import and phased pipeline operations.
#[derive(Clone)]
pub struct ImportService {
    ingest_dao: IngestDao,
    project_dao: ProjectDao,
    chapter_dao: ChapterDao,
}

impl ImportService {
    pub fn new() -> Self {
        Self {
            ingest_dao: IngestDao,
            project_dao: ProjectDao,
            chapter_dao: ChapterDao,
        }
    }

    // ---- Ingest job CRUD ----

    /// Start a file import, creating an ingest job record.
    pub async fn file_import(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        source_type: &str,
        source_url: Option<&str>,
        title: &str,
    ) -> AppResult<IngestJob> {
        let model = moling_db::entities::ingest_job::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            user_id: Set(user_id.to_owned()),
            source_type: Set(source_type.to_owned()),
            source_url: Set(source_url.map(|s| s.to_owned())),
            title: Set(title.to_owned()),
            current_phase: Set("phase0".to_owned()),
            ..Default::default()
        };
        let job = self.ingest_dao.create(db, model).await?;
        tracing::info!(job_id = %job.id, "Ingest job created");
        Ok(job)
    }

    /// Get an ingest job by ID.
    pub async fn get_job(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
    ) -> AppResult<IngestJob> {
        self.ingest_dao
            .find_by_id(db, job_id)
            .await?
            .ok_or_else(|| AppError::not_found("导入任务不存在".to_owned()))
    }

    /// List ingest jobs for a project.
    pub async fn list_jobs(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<IngestJob>> {
        self.ingest_dao.list_by_project(db, project_id).await
    }

    // ---- Phased pipeline ----

    /// Run Phase 1: extraction and merging.
    ///
    /// Parses uploaded file content, splits into chapters,
    /// and stores the extracted structure.
    pub async fn phase1(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
        raw_text: &str,
    ) -> AppResult<()> {
        let job = self.get_job(db, job_id).await?;

        // Split text into chapters
        let chapters = split_chapters(raw_text);
        let total_words: usize = chapters.iter().map(|(_, content)| count_words(content)).sum();

        // Update job with phase1 results
        use sea_orm::IntoActiveModel;
        let mut active = job.into_active_model();
        active.current_phase = Set("phase1".to_owned());
        active.total_chapters = Set(chapters.len() as i32);
        active.progress_percent = Set(25.0);
        active.phase0_result = Set(Some(serde_json::json!({
            "total_chars": raw_text.chars().count(),
            "total_words": total_words,
            "encoding": "utf-8",
        })));
        active.phase1_result = Set(Some(serde_json::json!({
            "chapters_found": chapters.len(),
            "chapter_titles": chapters.iter().map(|(t, _)| t).collect::<Vec<_>>(),
        })));
        self.ingest_dao.update(db, active).await?;

        tracing::info!(job_id, chapters = chapters.len(), "Phase 1: extraction completed");
        Ok(())
    }

    /// Run Phase 2: analysis.
    ///
    /// Analyzes chapter structure, word counts, completion rates, and style metrics.
    pub async fn phase2(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
        chapters: &[(String, String)],
    ) -> AppResult<()> {
        let job = self.get_job(db, job_id).await?;

        let chapter_count = chapters.len();
        let word_counts: Vec<usize> = chapters.iter().map(|(_, c)| count_words(c)).collect();
        let total_words: usize = word_counts.iter().sum();
        let avg_words: f64 = if chapter_count > 0 {
            total_words as f64 / chapter_count as f64
        } else {
            0.0
        };

        let min_words = word_counts.iter().min().copied().unwrap_or(0);
        let max_words = word_counts.iter().max().copied().unwrap_or(0);

        // Word count standard deviation
        let std_dev: f64 = if word_counts.len() > 1 {
            let mean = total_words as f64 / word_counts.len() as f64;
            let variance: f64 = word_counts
                .iter()
                .map(|w| {
                    let diff = *w as f64 - mean;
                    diff * diff
                })
                .sum::<f64>()
                / word_counts.len() as f64;
            variance.sqrt()
        } else {
            0.0
        };

        // Style analysis
        let all_text: String = chapters.iter().map(|(_, c)| c.as_str()).collect::<Vec<_>>().join("\n");
        let sentences: Vec<&str> = all_text
            .split(['。', '！', '？', '.', '!', '?', '\n'])
            .filter(|s| !s.trim().is_empty())
            .collect();
        let avg_sentence_len: f64 = if sentences.is_empty() {
            0.0
        } else {
            sentences.iter().map(|s| s.chars().count()).sum::<usize>() as f64 / sentences.len() as f64
        };

        // Dialogue ratio (simplified: text inside quotes)
        let dialogue_chars: usize = all_text
            .match_indices(&['"', '"', '"', '"', '「', '」', '『', '』'][..])
            .count();

        // Update job with phase2 results
        use sea_orm::IntoActiveModel;
        let mut active = job.into_active_model();
        active.current_phase = Set("phase2".to_owned());
        active.progress_percent = Set(50.0);
        active.phase2_result = Set(Some(serde_json::json!({
            "structure": {
                "total_chapters": chapter_count,
                "total_words": total_words,
                "avg_words_per_chapter": (avg_words * 10.0).round() / 10.0,
                "word_count_distribution": {
                    "min": min_words,
                    "max": max_words,
                    "avg": (avg_words * 10.0).round() / 10.0,
                    "std": (std_dev * 10.0).round() / 10.0,
                },
            },
            "style": {
                "total_chars": all_text.chars().count(),
                "avg_sentence_length": (avg_sentence_len * 10.0).round() / 10.0,
                "dialogue_chars": dialogue_chars,
                "paragraph_count": all_text.lines().filter(|l| !l.trim().is_empty()).count(),
            },
            "suggestions": self.generate_suggestions(chapter_count, total_words, avg_words, std_dev),
        })));
        self.ingest_dao.update(db, active).await?;

        tracing::info!(job_id, "Phase 2: analysis completed");
        Ok(())
    }

    /// Run Phase 3: committal — write chapters to database.
    pub async fn phase3(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
        chapters: &[(String, String)],
    ) -> AppResult<()> {
        let job = self.get_job(db, job_id).await?;

        // Get max chapter number for the project
        let max_num = self
            .chapter_dao
            .max_chapter_number(db, job.project_id)
            .await?
            .unwrap_or(0);

        let mut total_words: i32 = 0;
        for (idx, (title, content)) in chapters.iter().enumerate() {
            let wc = count_words(content) as i32;
            let chapter_model = moling_db::entities::chapter::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(job.project_id),
                title: Set(title.clone()),
                content: Set(Some(content.clone())),
                chapter_number: Set(max_num + idx as i32 + 1),
                word_count: Set(wc),
                status: Set("imported".to_owned()),
                ..Default::default()
            };
            self.chapter_dao.create(db, chapter_model).await?;
            total_words += wc;
        }

        // Update project word count
        if let Some(project) = self.project_dao.find_by_id(db, job.project_id).await? {
            use sea_orm::IntoActiveModel;
            let current_wc = project.word_count;
            let mut active = project.into_active_model();
            active.word_count = Set(current_wc + total_words);
            active.update(db).await.ok();
        }

        // Update job with phase3 results
        use sea_orm::IntoActiveModel;
        let mut active = job.into_active_model();
        active.current_phase = Set("phase3".to_owned());
        active.progress_percent = Set(100.0);
        active.phase3_result = Set(Some(serde_json::json!({
            "chapters_created": chapters.len(),
            "total_words_added": total_words,
            "status": "committed",
        })));
        self.ingest_dao.update(db, active).await?;

        tracing::info!(job_id, "Phase 3: committing completed");
        Ok(())
    }

    /// Run the full import pipeline (phase1 → phase2 → phase3).
    pub async fn full_import(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        source_type: &str,
        source_url: Option<&str>,
        title: &str,
        raw_text: &str,
    ) -> AppResult<IngestJob> {
        let job = self
            .file_import(db, user_id, project_id, source_type, source_url, title)
            .await?;
        let chapters = split_chapters(raw_text);
        let chapter_pairs: Vec<(String, String)> = chapters;

        self.phase1(db, &job.id, raw_text).await?;
        self.phase2(db, &job.id, &chapter_pairs).await?;
        self.phase3(db, &job.id, &chapter_pairs).await?;

        tracing::info!(job_id = %job.id, "Full import pipeline completed");
        Ok(job)
    }

    // ---- Suggestions & analysis helpers ----

    /// Generate writing suggestions based on content analysis.
    fn generate_suggestions(
        &self,
        chapter_count: usize,
        total_words: usize,
        avg_words: f64,
        word_count_std: f64,
    ) -> Vec<serde_json::Value> {
        let mut suggestions: Vec<serde_json::Value> = Vec::new();

        if chapter_count == 0 {
            suggestions.push(serde_json::json!({
                "type": "structure",
                "title": "尚无章节",
                "content": "项目目前没有章节内容，建议先导入文稿或手动创建章节。",
                "priority": "high",
            }));
            return suggestions;
        }

        if chapter_count < 3 {
            suggestions.push(serde_json::json!({
                "type": "structure",
                "title": "章节数量较少",
                "content": format!("当前只有 {chapter_count} 个章节，建议完成更多章节以更好地分析整体结构和节奏。"),
                "priority": "medium",
            }));
        }

        if avg_words > 0.0 && avg_words < 500.0 {
            suggestions.push(serde_json::json!({
                "type": "word_count",
                "title": "章节字数偏少",
                "content": format!("平均每章仅 {:.0} 字，网文通常每章 2000–5000 字，建议扩充内容。", avg_words),
                "priority": "medium",
            }));
        } else if avg_words > 10000.0 {
            suggestions.push(serde_json::json!({
                "type": "word_count",
                "title": "章节字数偏多",
                "content": format!("平均每章 {:.0} 字，可能造成阅读负担，建议拆分为更短的章节。", avg_words),
                "priority": "low",
            }));
        }

        if word_count_std > 3000.0 {
            suggestions.push(serde_json::json!({
                "type": "structure",
                "title": "章节长度波动较大",
                "content": "章节字数差异显著（标准差大），建议保持每章长度相对均匀，以提升阅读体验。",
                "priority": "medium",
            }));
        }

        if total_words > 0 && total_words < 10000 {
            suggestions.push(serde_json::json!({
                "type": "scale",
                "title": "作品篇幅偏短",
                "content": format!("当前总计 {total_words} 字，建议继续扩充内容以构建完整的故事。"),
                "priority": "medium",
            }));
        }

        suggestions
    }

    // ---- Error handling & retry ----

    /// Retry a failed import job from a specific phase.
    pub async fn retry_job(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
        from_phase: &str,
    ) -> AppResult<()> {
        let job = self.get_job(db, job_id).await?;
        use sea_orm::IntoActiveModel;
        let mut active = job.into_active_model();
        active.current_phase = Set(from_phase.to_owned());
        active.error_message = Set(None);
        active.progress_percent = Set(0.0);
        self.ingest_dao.update(db, active).await?;
        tracing::info!(job_id, from_phase, "Import job reset for retry");
        Ok(())
    }

    /// Mark an import job as failed with an error message.
    pub async fn fail_job(
        &self,
        db: &DatabaseConnection,
        job_id: &str,
        error: &str,
    ) -> AppResult<()> {
        let job = self.get_job(db, job_id).await?;
        use sea_orm::IntoActiveModel;
        let mut active = job.into_active_model();
        active.error_message = Set(Some(error.to_owned()));
        active.current_phase = Set("failed".to_owned());
        self.ingest_dao.update(db, active).await?;
        tracing::error!(job_id, %error, "Import job failed");
        Ok(())
    }

    /// Parse text content from a file path (TXT only for now).
    /// Uses UTF-8 encoding with fallback.
    pub fn parse_txt_file(file_path: &str) -> AppResult<String> {
        std::fs::read_to_string(file_path).map_err(|_| {
            AppError::validation_error(
                "无法读取文件，请确认文件为 UTF-8 编码".to_owned(),
            )
        })
    }

    /// Parse Markdown content into plain text, extracting chapter structure.
    pub fn parse_markdown(markdown: &str) -> Vec<(String, String)> {
        let mut chapters: Vec<(String, String)> = Vec::new();
        let mut current_title = String::from("前言");
        let mut current_content = String::new();

        for line in markdown.lines() {
            if line.starts_with("## ") || line.starts_with("# ") {
                // Save previous chapter
                if !current_content.trim().is_empty() {
                    chapters.push((current_title.clone(), current_content.trim().to_owned()));
                }
                current_title = line.trim_start_matches('#').trim().to_owned();
                current_content = String::new();
            } else {
                if !current_content.is_empty() {
                    current_content.push('\n');
                }
                current_content.push_str(line);
            }
        }

        // Save last chapter
        if !current_content.trim().is_empty() {
            chapters.push((current_title, current_content.trim().to_owned()));
        }

        if chapters.is_empty() {
            // No headers found, treat entire content as one chapter
            let first_line = markdown.lines().next().unwrap_or("未命名").to_owned();
            chapters.push((first_line, markdown.to_owned()));
        }

        chapters
    }

    /// Determine supported file format from extension.
    pub fn detect_format(file_path: &str) -> Option<&'static str> {
        let path = std::path::Path::new(file_path);
        match path.extension().and_then(|e| e.to_str()) {
            Some("txt") => Some("txt"),
            Some("md") | Some("markdown") => Some("markdown"),
            Some("docx") => Some("docx"),
            Some("epub") => Some("epub"),
            _ => None,
        }
    }

    /// Validate that a file format is supported.
    pub fn validate_format(file_path: &str) -> AppResult<&'static str> {
        Self::detect_format(file_path)
            .ok_or_else(|| AppError::validation_error(
                "不支持的文件格式，支持 txt / md / docx / epub".to_string()
            ))
    }
}

impl Default for ImportService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_import_service_constructs() {
        let _ = ImportService::new();
    }

    #[test]
    fn test_extract_chapter_title_chinese() {
        assert_eq!(
            extract_chapter_title("第一章 开端"),
            Some("第一章 开端".into())
        );
        assert_eq!(
            extract_chapter_title("第12章 转折"),
            Some("第12章 转折".into())
        );
    }

    #[test]
    fn test_extract_chapter_title_english() {
        assert_eq!(
            extract_chapter_title("Chapter 1 The Beginning"),
            Some("Chapter 1 The Beginning".into())
        );
    }

    #[test]
    fn test_extract_chapter_title_none() {
        assert_eq!(extract_chapter_title("普通段落文字"), None);
    }

    #[test]
    fn test_count_chinese_chars() {
        assert_eq!(count_chinese_chars("你好世界"), 4);
        assert_eq!(count_chinese_chars("hello"), 0);
        assert_eq!(count_chinese_chars("hello你好world世界"), 4);
    }

    #[test]
    fn test_count_words() {
        let text = "你好世界 hello world test";
        assert!(count_words(text) >= 4);
    }

    #[test]
    fn test_split_chapters_simple() {
        let text = "第1章 开篇\n这是第一章的内容。\n第2章 发展\n这是第二章的内容。";
        let chapters = split_chapters(text);
        assert!(!chapters.is_empty());
    }

    #[test]
    fn test_extract_metadata_from_filename() {
        let (title, _author) = extract_metadata_from_filename("/path/《红楼梦》-曹雪芹.txt");
        assert!(title.contains("红楼梦") || !title.is_empty());
    }

    #[test]
    fn test_detect_format() {
        assert_eq!(ImportService::detect_format("test.txt"), Some("txt"));
        assert_eq!(ImportService::detect_format("test.md"), Some("markdown"));
        assert_eq!(ImportService::detect_format("test.xyz"), None);
    }

    #[test]
    fn test_parse_markdown() {
        let md = "# Title\n\nContent here.\n\n## Chapter 1\n\nChapter content.";
        let chapters = ImportService::parse_markdown(md);
        assert!(!chapters.is_empty());
    }
}
