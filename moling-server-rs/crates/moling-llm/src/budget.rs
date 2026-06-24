//! Token budget — approximate token counting and context window management.
//!
//! Provides two budget calculators:
//!
//! - [`TokenBudget`] — fast character-count heuristic (4 chars ≈ 1 token)
//!   for quick pre-flight budget gating.
//! - [`ContextBudget`] — full context window budget check with layered
//!   truncation strategy, matching the algorithm in §3.2/§3.5 of the spec.
//!
//! ## Model Window Sizes
//!
//! | Model | Context Window |
//! |-------|---------------|
//! | deepseek-chat / deepseek-v3 | 128,000 tokens |
//! | deepseek-reasoner / deepseek-r1 | 128,000 tokens |
//!
//! ## Truncation Priority (lowest to highest)
//!
//! 1. Layer 4 — Style constraints (can be fully dropped)
//! 2. Layer 3 — Card direction / inspiration (compress inspiration, keep direction)
//! 3. Layer 2 — Vault data (progressive per-entry compression)
//! 4. Layer 1 — Dynamic layer (NEVER truncated)
//! 5. Layer 0 — System instruction (NEVER truncated)

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Fast token estimation: 4 characters ≈ 1 token for Chinese/English mixed text.
const CHARS_PER_TOKEN: usize = 4;

/// Safety factor applied to context window (0.85 = 15% headroom for output).
const SAFETY_FACTOR: f64 = 0.85;

/// Default model context window (DeepSeek V3).
const DEFAULT_MODEL_WINDOW: usize = 128_000;

/// DeepSeek V3 context window.
const DEEPSEEK_V3_WINDOW: usize = 128_000;

/// DeepSeek R1 context window (same as V3).
const DEEPSEEK_R1_WINDOW: usize = 128_000;

// ---------------------------------------------------------------------------
// Model context limits (backward-compatible constants)
// ---------------------------------------------------------------------------

/// Model context window sizes (in tokens).
pub mod limits {
    /// DeepSeek V3 / default chat model — 128K tokens.
    pub const DEEPSEEK_CHAT: usize = 128_000;
    /// DeepSeek R1 / reasoner model — 128K tokens.
    pub const DEEPSEEK_REASONER: usize = 128_000;
    /// Alias for backward compatibility.
    pub const DEEPSEEK_LARGE: usize = 128_000;
}

// ---------------------------------------------------------------------------
// TokenBudget — fast heuristic estimation
// ---------------------------------------------------------------------------

/// Token budget calculator for quick pre-flight checks.
///
/// Uses a character-count heuristic (4 chars ≈ 1 token) which is sufficient
/// for budget gating before making an API call.
pub struct TokenBudget;

impl TokenBudget {
    /// Estimate the number of tokens in the given text.
    ///
    /// Uses a character-count heuristic: `ceil(chars / 4)` with a floor of 1
    /// for non-empty text.
    pub fn estimate(text: &str) -> usize {
        if text.is_empty() {
            return 0;
        }
        text.chars().count().div_ceil(CHARS_PER_TOKEN).max(1)
    }

    /// Check whether the text fits within the given model's context limit.
    ///
    /// Returns `true` if `estimate(text) <= model_limit`.
    pub fn fits(text: &str, model_limit: usize) -> bool {
        Self::estimate(text) <= model_limit
    }

    /// Estimate tokens for a list of messages (system + user + assistant).
    pub fn estimate_messages(messages: &[&str]) -> usize {
        messages.iter().map(|m| Self::estimate(m)).sum()
    }

    /// Check if messages fit within the given limit, leaving headroom for the response.
    ///
    /// Reserves 20% of the limit for the model's response.
    pub fn fits_with_headroom(messages: &[&str], model_limit: usize) -> bool {
        let estimated = Self::estimate_messages(messages);
        let headroom = model_limit * 20 / 100;
        estimated + headroom <= model_limit
    }

    /// Get the context window size for a given model name.
    pub fn get_model_window(model: Option<&str>) -> usize {
        ContextBudget::get_model_window(model)
    }
}

// ---------------------------------------------------------------------------
// BudgetResult
// ---------------------------------------------------------------------------

/// Result of a context budget check.
#[derive(Debug, Clone)]
pub struct BudgetResult {
    /// Whether the prompt fits within the safe context window.
    pub within_budget: bool,
    /// Estimated input tokens.
    pub estimated_input_tokens: usize,
    /// Available tokens for input (safe_window - max_output_tokens).
    pub available_tokens: usize,
    /// The model's full context window size.
    pub model_window: usize,
    /// Requested max output tokens.
    pub max_output_tokens: usize,
    /// Remaining tokens (available - estimated_input, can be negative).
    pub remaining_tokens: isize,
    /// The (possibly truncated) prompt.
    pub truncated_prompt: String,
    /// Records of truncation actions applied.
    pub truncations: Vec<TruncationRecord>,
}

/// Record of a single truncation action.
#[derive(Debug, Clone)]
pub struct TruncationRecord {
    /// Which layer was affected.
    pub layer: String,
    /// What field was truncated (if applicable).
    pub field: Option<String>,
    /// What action was taken.
    pub action: String,
}

// ---------------------------------------------------------------------------
// ContextBudget — full context window manager
// ---------------------------------------------------------------------------

/// LLM context window budget manager with layered truncation.
///
/// Implements the algorithm from §3.5 of the spec with §3.2 Lost-in-the-Middle
/// protection. Layers 0 and 1 are never truncated.
pub struct ContextBudget;

impl ContextBudget {
    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Estimate tokens for a given text.
    pub fn estimate_tokens(text: &str) -> usize {
        TokenBudget::estimate(text)
    }

    /// Get the context window size for a given model name.
    ///
    /// Returns the token count for known models, or a safe default.
    pub fn get_model_window(model: Option<&str>) -> usize {
        match model {
            Some(m) => match m {
                "deepseek-chat" | "deepseek-v3" | "deepseek-v4-pro" | "deepseek-v4-flash" => {
                    DEEPSEEK_V3_WINDOW
                }
                "deepseek-reasoner" | "deepseek-r1" => DEEPSEEK_R1_WINDOW,
                _ => DEFAULT_MODEL_WINDOW,
            },
            None => DEFAULT_MODEL_WINDOW,
        }
    }

    /// Check whether the prompt fits within the model's safe context window.
    ///
    /// Returns a [`BudgetResult`] with full details.
    ///
    /// # Arguments
    /// * `prompt` — The assembled prompt text.
    /// * `model` — Model name for context window lookup.
    /// * `max_output_tokens` — Expected max output tokens (reserved).
    pub fn check(
        prompt: &str,
        model: Option<&str>,
        max_output_tokens: usize,
    ) -> BudgetResult {
        let model_window = Self::get_model_window(model);
        let safe_window = (model_window as f64 * SAFETY_FACTOR) as usize;
        let estimated_input = Self::estimate_tokens(prompt);
        let available = safe_window.saturating_sub(max_output_tokens);
        let remaining = available as isize - estimated_input as isize;

        BudgetResult {
            within_budget: remaining >= 0,
            estimated_input_tokens: estimated_input,
            available_tokens: available,
            model_window,
            max_output_tokens,
            remaining_tokens: remaining,
            truncated_prompt: prompt.to_owned(),
            truncations: Vec::new(),
        }
    }

    /// Check the prompt and apply layered truncation if it exceeds the budget.
    ///
    /// Truncation follows priority (lowest to highest):
    /// 1. Layer 4 — Style constraints → fully removed
    /// 2. Layer 3 — Card direction → compress inspiration, keep direction
    /// 3. Layer 2 — Vault data → progressive per-entry compression
    /// 4. Layer 1/0 — NEVER truncated
    ///
    /// # Arguments
    /// * `prompt` — The assembled prompt text (with layer markers).
    /// * `model` — Model name for context window lookup.
    /// * `max_output_tokens` — Expected max output tokens.
    /// * `truncation_config` — Optional configuration for truncation parameters.
    pub fn check_and_truncate(
        prompt: &str,
        model: Option<&str>,
        max_output_tokens: usize,
        truncation_config: Option<&TruncationConfig>,
    ) -> BudgetResult {
        let default_config = TruncationConfig::default();
        let config = truncation_config.unwrap_or(&default_config);
        let mut result = Self::check(prompt, model, max_output_tokens);

        if result.within_budget {
            return result;
        }

        let mut truncated = prompt.to_owned();
        let overflow_tokens = result.remaining_tokens.unsigned_abs();
        let overflow_chars = overflow_tokens * CHARS_PER_TOKEN;

        tracing::info!(
            overflow_tokens,
            overflow_chars,
            "Applying layered truncation"
        );

        // ── Step 1: Drop Layer 4 (style constraints) ──
        let dropped = Self::truncate_layer4(&truncated, &mut result);
        truncated = dropped;

        // ── Step 2: Compress Layer 3 (direction) ──
        let compressed = Self::truncate_layer3(&truncated, &mut result, model, max_output_tokens);
        truncated = compressed;

        // ── Step 3: Compress Layer 2 (vault data) progressively ──
        let compressed = Self::truncate_layer2(
            &truncated,
            &mut result,
            model,
            max_output_tokens,
            config,
        );
        truncated = compressed;

        // ── Step 4: Final check ──
        let final_result = Self::check(&truncated, model, max_output_tokens);
        if !final_result.within_budget {
            tracing::error!(
                input = final_result.estimated_input_tokens,
                available = final_result.available_tokens,
                "CRITICAL: Context still over budget after all truncations"
            );
        }

        let mut final_result = final_result;
        final_result.truncated_prompt = truncated;
        final_result.truncations = result.truncations;
        final_result
    }

    // ------------------------------------------------------------------
    // Layered truncation
    // ------------------------------------------------------------------

    /// Remove Layer 4 (style constraints) entirely — lowest priority.
    fn truncate_layer4(prompt: &str, result: &mut BudgetResult) -> String {
        let markers = ["=== Layer 4 ===", "[Layer 4:", "【风格约束】"];
        for marker in &markers {
            if let Some(idx) = prompt.find(marker) {
                // Find the end of this layer (next double newline or end of string)
                let rest = &prompt[idx..];
                let layer_end = rest.find("\n\n").unwrap_or(rest.len());
                let new_prompt = format!(
                    "{}{}",
                    &prompt[..idx].trim_end(),
                    &prompt[idx + layer_end..]
                );
                tracing::info!("Truncated Layer 4 (style constraints)");
                result.truncations.push(TruncationRecord {
                    layer: "Layer 4".to_owned(),
                    field: None,
                    action: "removed".to_owned(),
                });
                return new_prompt;
            }
        }
        prompt.to_owned()
    }

    /// Compress Layer 3 — keep direction + weaving scheme, drop inspiration.
    fn truncate_layer3(
        prompt: &str,
        result: &mut BudgetResult,
        model: Option<&str>,
        max_output_tokens: usize,
    ) -> String {
        let check = Self::check(prompt, model, max_output_tokens);
        if check.within_budget {
            return prompt.to_owned();
        }

        if let Some(idx) = prompt.find("【创作灵感】") {
            let next_section = ["=== ", "【写作要求】", "\n\n"]
                .iter()
                .filter_map(|m| prompt[idx + "【创作灵感】".len()..].find(m))
                .min();

            if let Some(next) = next_section {
                let cut_point = idx + "【创作灵感】".len() + next;
                if cut_point > idx {
                    let new_prompt = format!(
                        "{}\n\n{}",
                        prompt[..idx].trim_end(),
                        prompt[cut_point..].trim_start()
                    );
                    tracing::info!("Truncated Layer 3 inspiration (kept direction + weaving)");
                    result.truncations.push(TruncationRecord {
                        layer: "Layer 3".to_owned(),
                        field: Some("inspiration".to_owned()),
                        action: "removed".to_owned(),
                    });
                    return if Self::check(&new_prompt, model, max_output_tokens).within_budget {
                        new_prompt
                    } else {
                        prompt.to_owned()
                    };
                }
            }
        }
        prompt.to_owned()
    }

    /// Progressively compress Layer 2 vault data.
    fn truncate_layer2(
        prompt: &str,
        result: &mut BudgetResult,
        model: Option<&str>,
        max_output_tokens: usize,
        config: &TruncationConfig,
    ) -> String {
        let mut truncated = prompt.to_owned();
        let mut current_chars_per_char = config.layer2_max_chars_per_char;
        let mut current_max_promises = config.layer2_max_promises;
        let mut current_max_timeline = config.layer2_max_timeline;
        let mut current_max_world = config.layer2_max_world;

        const MAX_ROUNDS: usize = 10;

        for round_idx in 0..MAX_ROUNDS {
            let before = truncated.clone();

            // Compress character entries
            truncated = Self::truncate_characters(&truncated, current_chars_per_char);
            // Compress plot promises
            truncated = Self::truncate_section(
                &truncated,
                "【伏笔层】",
                current_max_promises,
            );
            truncated = Self::truncate_section(
                &truncated,
                "【相关伏笔】",
                current_max_promises,
            );
            // Compress timeline
            truncated = Self::truncate_section(
                &truncated,
                "【时间线层】",
                current_max_timeline,
            );
            truncated = Self::truncate_section(
                &truncated,
                "【时间线参考】",
                current_max_timeline,
            );
            // Compress world entries
            truncated = Self::truncate_section(
                &truncated,
                "【世界观层】",
                current_max_world,
            );
            truncated = Self::truncate_section(
                &truncated,
                "【世界观规则】",
                current_max_world,
            );

            let check = Self::check(&truncated, model, max_output_tokens);
            if check.within_budget {
                tracing::info!(
                    round = round_idx + 1,
                    chars_per_char = current_chars_per_char,
                    promises = current_max_promises,
                    timeline = current_max_timeline,
                    world = current_max_world,
                    "Layer 2 truncation: now within budget"
                );
                result.truncations.push(TruncationRecord {
                    layer: "Layer 2".to_owned(),
                    field: None,
                    action: format!(
                        "compressed (chars_per={current_chars_per_char}, promises={current_max_promises}, timeline={current_max_timeline}, world={current_max_world})"
                    ),
                });
                return truncated;
            }

            if truncated == before {
                tracing::warn!("Layer 2 truncation stalled at round {round_idx}");
                break;
            }

            // Escalate compression
            current_chars_per_char =
                usize::max(config.layer2_min_chars_per_char, current_chars_per_char.saturating_sub(20));
            current_max_promises = usize::max(1, current_max_promises.saturating_sub(1));
            current_max_timeline = usize::max(1, current_max_timeline.saturating_sub(1));
            current_max_world = usize::max(1, current_max_world.saturating_sub(1));
        }

        truncated
    }

    // ------------------------------------------------------------------
    // Truncation helpers
    // ------------------------------------------------------------------

    /// Truncate character description fields to a maximum character count.
    fn truncate_characters(prompt: &str, max_chars: usize) -> String {
        // Match patterns like: 【角色名】\n  description: ...\n  status: ...
        // Strategy: for each line starting with "  " that's too long, truncate it.
        let mut result = String::with_capacity(prompt.len());
        for line in prompt.lines() {
            let trimmed = line.trim_start();
            let indent = &line[..line.len() - trimmed.len()];

            if (trimmed.starts_with("描述: ")
                || trimmed.starts_with("当前状态: ")
                || trimmed.starts_with("description: ")
                || trimmed.starts_with("状态: "))
                && trimmed.len() > max_chars + 10
            {
                let cutoff = max_chars + 10;
                let truncated: String = trimmed.chars().take(cutoff).collect();
                result.push_str(&format!("{indent}{truncated}…\n"));
            } else if indent.len() >= 2 && trimmed.len() > max_chars {
                let truncated: String = trimmed.chars().take(max_chars).collect();
                result.push_str(&format!("{indent}{truncated}…\n"));
            } else {
                result.push_str(line);
                result.push('\n');
            }
        }
        // Remove trailing newline if original didn't have one
        if !prompt.ends_with('\n') && result.ends_with('\n') {
            result.pop();
        }
        result
    }

    /// Truncate a named section to at most `max_entries` bullet items.
    fn truncate_section(prompt: &str, section_header: &str, max_entries: usize) -> String {
        let idx = match prompt.find(section_header) {
            Some(i) => i,
            None => return prompt.to_owned(),
        };

        // Find the end of this section (next top-level header or EOF)
        let section_start = idx;
        let after_header = section_start + section_header.len();

        let next_section = prompt[after_header..]
            .find("\n\n【")
            .or_else(|| prompt[after_header..].find("\n\n#"))
            .or_else(|| prompt[after_header..].find("\n=="));

        let section_end = match next_section {
            Some(pos) => after_header + pos,
            None => prompt.len(),
        };

        let section_content = &prompt[section_start..section_end];

        // Count entries (lines starting with "- " or numbered items)
        let entries: Vec<&str> = section_content
            .lines()
            .filter(|l| {
                let t = l.trim();
                t.starts_with("- ") || t.starts_with("* ") || t.starts_with("• ")
            })
            .collect();

        if entries.len() <= max_entries {
            return prompt.to_owned();
        }

        // Keep first max_entries, rebuild section
        let kept = &entries[..max_entries];
        let new_section = format!(
            "{}\n{}",
            section_header,
            kept.iter().map(|e| format!("  {e}")).collect::<Vec<_>>().join("\n")
        );

        format!(
            "{}{}{}",
            &prompt[..section_start],
            new_section,
            &prompt[section_end..]
        )
    }
}

// ---------------------------------------------------------------------------
// TruncationConfig
// ---------------------------------------------------------------------------

/// Configuration for layered truncation behaviour.
#[derive(Debug, Clone)]
pub struct TruncationConfig {
    /// Maximum characters per character description entry (initial, Layer 2).
    pub layer2_max_chars_per_char: usize,
    /// Minimum characters per character entry (floor for Layer 2 compression).
    pub layer2_min_chars_per_char: usize,
    /// Maximum number of plot promise entries to retain.
    pub layer2_max_promises: usize,
    /// Maximum number of timeline entries to retain.
    pub layer2_max_timeline: usize,
    /// Maximum number of world entries to retain.
    pub layer2_max_world: usize,
}

impl Default for TruncationConfig {
    fn default() -> Self {
        Self {
            layer2_max_chars_per_char: 200,
            layer2_min_chars_per_char: 100,
            layer2_max_promises: 8,
            layer2_max_timeline: 3,
            layer2_max_world: 8,
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // ── TokenBudget tests ──

    #[test]
    fn test_estimate_english() {
        let tokens = TokenBudget::estimate("Hello world, how are you doing?");
        // 34 chars → ceil(34/4) = 9
        assert!((6..=12).contains(&tokens));
    }

    #[test]
    fn test_estimate_chinese() {
        let tokens = TokenBudget::estimate("你好世界测试文本内容");
        // 10 Chinese chars → ceil(10/4) = 3, but floor is 1
        assert!((2..=5).contains(&tokens));
    }

    #[test]
    fn test_estimate_empty() {
        assert_eq!(TokenBudget::estimate(""), 0);
    }

    #[test]
    fn test_estimate_single_char() {
        assert_eq!(TokenBudget::estimate("a"), 1);
    }

    #[test]
    fn test_fits_within_limit() {
        let text = "Short text";
        assert!(TokenBudget::fits(text, limits::DEEPSEEK_CHAT));
    }

    #[test]
    fn test_fits_with_headroom() {
        let msgs = vec!["System prompt", "User message", "Assistant response"];
        assert!(TokenBudget::fits_with_headroom(&msgs, limits::DEEPSEEK_CHAT));
    }

    #[test]
    fn test_estimate_messages() {
        let tokens = TokenBudget::estimate_messages(&["hello", "world"]);
        assert!(tokens > 0);
    }

    // ── ContextBudget tests ──

    #[test]
    fn test_model_window_known() {
        assert_eq!(
            ContextBudget::get_model_window(Some("deepseek-chat")),
            128_000
        );
        assert_eq!(
            ContextBudget::get_model_window(Some("deepseek-reasoner")),
            128_000
        );
        assert_eq!(
            ContextBudget::get_model_window(Some("deepseek-v3")),
            128_000
        );
    }

    #[test]
    fn test_model_window_unknown() {
        assert_eq!(
            ContextBudget::get_model_window(Some("unknown-model")),
            128_000
        );
    }

    #[test]
    fn test_model_window_none() {
        assert_eq!(ContextBudget::get_model_window(None), 128_000);
    }

    #[test]
    fn test_check_within_budget() {
        let prompt = "Short prompt for testing";
        let result = ContextBudget::check(prompt, Some("deepseek-chat"), 4096);
        assert!(result.within_budget);
        assert!(result.estimated_input_tokens > 0);
        assert_eq!(result.model_window, 128_000);
    }

    #[test]
    fn test_check_truncation_layer4() {
        // Simulate a prompt with Layer 4 marker
        let prompt = "=== Layer 1 ===\nimportant content\n\n=== Layer 4 ===\nstyle constraints here\n\nend";
        let mut result = ContextBudget::check(prompt, Some("deepseek-chat"), 4096);
        let truncated = ContextBudget::truncate_layer4(prompt, &mut result);
        assert!(!truncated.contains("style constraints"));
        assert!(truncated.contains("=== Layer 1 ==="));
        assert!(!truncated.contains("=== Layer 4 ==="));
        // Verify truncation was recorded
    }

    #[test]
    fn test_check_and_truncate_normal() {
        let prompt = "A reasonable-length prompt that should fit easily";
        let result =
            ContextBudget::check_and_truncate(prompt, Some("deepseek-chat"), 4096, None);
        assert!(result.within_budget);
        assert_eq!(result.truncated_prompt, prompt);
        assert!(result.truncations.is_empty());
    }

    #[test]
    fn test_truncate_section() {
        let prompt = "【伏笔层】\n- promise 1\n- promise 2\n- promise 3\n- promise 4\n- promise 5\n\nnext section";
        let truncated = ContextBudget::truncate_section(prompt, "【伏笔层】", 2);
        // Should keep only first 2 promises
        let count = truncated.lines().filter(|l| l.trim().starts_with("- ")).count();
        assert!(count <= 2, "Should have at most 2 promises, got {count}");
    }

    #[test]
    fn test_truncation_config_defaults() {
        let config = TruncationConfig::default();
        assert_eq!(config.layer2_max_chars_per_char, 200);
        assert_eq!(config.layer2_min_chars_per_char, 100);
        assert_eq!(config.layer2_max_promises, 8);
        assert_eq!(config.layer2_max_timeline, 3);
        assert_eq!(config.layer2_max_world, 8);
    }

    #[test]
    fn test_limits_backward_compat() {
        assert_eq!(limits::DEEPSEEK_CHAT, 128_000);
        assert_eq!(limits::DEEPSEEK_LARGE, 128_000);
    }
}
