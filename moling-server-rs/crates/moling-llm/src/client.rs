//! DeepSeek API client — synchronous and streaming chat completions.
//!
//! Communicates with OpenAI-compatible `/v1/chat/completions` endpoints.
//! Supports both single-response and SSE streaming via `reqwest`.
//!
//! Features:
//! - Retry with exponential backoff (up to 3 attempts)
//! - Rate limit tracking per API key
//! - Full error classification (429, timeout, connection errors)
//! - Integration with [`KeyRotator`](crate::key_rotator::KeyRotator)

use futures::stream::BoxStream;
use futures::StreamExt;
use moling_core::error::{AppError, AppResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use crate::key_rotator::{KeyRotator, Pool};
use crate::retry::{extract_retry_after, RetryPolicy};

/// Default API base URL (DeepSeek).
pub const DEFAULT_BASE_URL: &str = "https://api.deepseek.com";

/// Default request timeout (seconds).
const DEFAULT_TIMEOUT_SECS: u64 = 180;

/// Default model name.
pub const DEFAULT_MODEL: &str = "deepseek-chat";

/// Maximum retry attempts for transient failures.
const MAX_RETRIES: u32 = 3;

/// Minimum backoff duration between retries.
#[allow(dead_code)]
const RETRY_MIN_BACKOFF_SECS: u64 = 1;

/// Maximum backoff duration between retries.
#[allow(dead_code)]
const RETRY_MAX_BACKOFF_SECS: u64 = 10;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// A chat message with role and content.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

impl ChatMessage {
    /// Create a system message.
    pub fn system(content: impl Into<String>) -> Self {
        Self {
            role: "system".into(),
            content: content.into(),
        }
    }

    /// Create a user message.
    pub fn user(content: impl Into<String>) -> Self {
        Self {
            role: "user".into(),
            content: content.into(),
        }
    }

    /// Create an assistant message.
    pub fn assistant(content: impl Into<String>) -> Self {
        Self {
            role: "assistant".into(),
            content: content.into(),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stream: Option<bool>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct ChatResponse {
    choices: Vec<Choice>,
    #[serde(default)]
    usage: Option<Usage>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: Option<ChoiceMessage>,
    delta: Option<ChoiceDelta>,
    #[serde(default, rename = "finish_reason")]
    _finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ChoiceMessage {
    content: String,
}

#[derive(Debug, Deserialize)]
struct ChoiceDelta {
    content: Option<String>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct Usage {
    #[serde(default, rename = "completion_tokens")]
    completion_tokens: u32,
    #[serde(default, rename = "prompt_tokens")]
    prompt_tokens: u32,
    #[serde(default, rename = "total_tokens")]
    total_tokens: u32,
}

#[derive(Debug, Deserialize)]
struct ErrorResponse {
    error: Option<ApiError>,
}

#[derive(Debug, Deserialize)]
struct ApiError {
    message: String,
    #[serde(default)]
    code: Option<String>,
}

// ---------------------------------------------------------------------------
// Rate Limit Tracker
// ---------------------------------------------------------------------------

/// Tracks rate limits per API key to avoid overwhelming the upstream service.
///
/// Maintains rolling 60-second windows for both request count and token count.
pub struct RateLimitTracker {
    /// Per-key request timestamps in the last 60 seconds.
    requests: Mutex<HashMap<String, Vec<Instant>>>,
    /// Per-key token counts in the last 60 seconds.
    tokens: Mutex<HashMap<String, Vec<u32>>>,
    /// Maximum requests per minute per key.
    max_requests_per_minute: u32,
    /// Maximum tokens per minute per key.
    max_tokens_per_minute: u32,
}

impl RateLimitTracker {
    /// Create a new rate limit tracker with default limits.
    ///
    /// Defaults: 60 requests/min, 40,000 tokens/min per key.
    pub fn new() -> Self {
        Self {
            requests: Mutex::new(HashMap::new()),
            tokens: Mutex::new(HashMap::new()),
            max_requests_per_minute: 60,
            max_tokens_per_minute: 40_000,
        }
    }

    /// Create a tracker with custom limits.
    pub fn with_limits(max_requests_per_minute: u32, max_tokens_per_minute: u32) -> Self {
        Self {
            requests: Mutex::new(HashMap::new()),
            tokens: Mutex::new(HashMap::new()),
            max_requests_per_minute,
            max_tokens_per_minute,
        }
    }

    /// Check if a request can be made within rate limits for the given key.
    pub fn can_make_request(&self, key: &str, estimated_tokens: u32) -> bool {
        let now = Instant::now();
        let window = Duration::from_secs(60);

        let mut reqs = self.requests.lock().unwrap_or_else(|e| e.into_inner());
        let mut toks = self.tokens.lock().unwrap_or_else(|e| e.into_inner());

        // Prune expired entries
        if let Some(timestamps) = reqs.get_mut(key) {
            timestamps.retain(|t| now.duration_since(*t) < window);
        }
        if let Some(token_counts) = toks.get_mut(key) {
            let req_entry = reqs.entry(key.to_owned()).or_default();
            // Align tokens with requests — prune any token count whose
            // corresponding request timestamp has been removed.
            token_counts.truncate(req_entry.len());
        }

        let req_count = reqs.get(key).map(|v| v.len()).unwrap_or(0) as u32;
        if req_count >= self.max_requests_per_minute {
            tracing::warn!(
                key = %mask_key(key),
                "Rate limit: too many requests for key"
            );
            return false;
        }

        let token_total: u32 = toks.get(key).map(|v| v.iter().sum()).unwrap_or(0);
        if token_total + estimated_tokens > self.max_tokens_per_minute {
            tracing::warn!(
                key = %mask_key(key),
                "Rate limit: token budget exceeded for key"
            );
            return false;
        }

        true
    }

    /// Record a successful request with its token count.
    pub fn record_request(&self, key: &str, token_count: u32) {
        let now = Instant::now();
        let mut reqs = self.requests.lock().unwrap_or_else(|e| e.into_inner());
        let mut toks = self.tokens.lock().unwrap_or_else(|e| e.into_inner());

        reqs.entry(key.to_owned()).or_default().push(now);
        toks.entry(key.to_owned()).or_default().push(token_count);
    }

    /// Get recommended wait time in seconds before the next request.
    ///
    /// Returns 0.0 if a request can be made immediately.
    pub fn get_wait_time(&self, key: &str) -> f64 {
        if self.can_make_request(key, 0) {
            return 0.0;
        }

        let reqs = self.requests.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(timestamps) = reqs.get(key) {
            if let Some(oldest) = timestamps.iter().min() {
                let elapsed = oldest.elapsed().as_secs_f64();
                let wait = 60.0 - elapsed;
                return f64::max(wait, 0.1);
            }
        }
        0.1
    }
}

impl Default for RateLimitTracker {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Error classification
// ---------------------------------------------------------------------------

/// Classify an HTTP status code into an [`AppError`], extracting `Retry-After` if present.
///
/// Returns `(AppError, Option<u64>)` where the second element is the
/// `Retry-After` value in seconds (only for 429 responses).
fn build_error(status_code: u16, headers: &reqwest::header::HeaderMap, body: &str) -> (AppError, Option<u64>) {
    let detail = serde_json::from_str::<ErrorResponse>(body)
        .ok()
        .and_then(|e| e.error)
        .map(|e| {
            if let Some(code) = e.code {
                format!("[{}] {}", code, e.message)
            } else {
                e.message
            }
        })
        .unwrap_or_else(|| format!("HTTP {status_code}: {body}"));

    let retry_after = extract_retry_after(headers);

    match status_code {
        429 => (
            AppError::with_detail(
                moling_core::error::ErrorCode::RateLimitExceeded,
                detail,
            ),
            retry_after,
        ),
        _ => (
            AppError::internal(format!("LLM API error: {detail}")),
            None,
        ),
    }
}

/// Determine if an error is retryable (transient network or server errors).
fn is_retryable(err: &AppError) -> bool {
    let msg = err.message.to_lowercase();
    msg.contains("timeout")
        || msg.contains("connect")
        || msg.contains("connection")
        || msg.contains("eof")
        || msg.contains("reset")
        || msg.contains("stream")
        || msg.contains("429")
        || msg.contains("rate_limit")
        || msg.contains("too many requests")
}

// ---------------------------------------------------------------------------
// DeepSeekClient
// ---------------------------------------------------------------------------

/// DeepSeek API client with configurable base URL, timeout, and retry policy.
///
/// Supports both non-streaming `chat()` and SSE streaming `chat_stream()`.
/// Integrates with [`KeyRotator`](crate::key_rotator::KeyRotator) for API key
/// management and automatic failover.
///
/// # Example
///
/// ```ignore
/// let client = DeepSeekClient::new();
/// let messages = vec![ChatMessage::user("你好".to_owned())];
/// let response = client.chat(&messages, "sk-xxx", "deepseek-chat", 0.7, 4096).await?;
/// ```
pub struct DeepSeekClient {
    base_url: String,
    client: reqwest::Client,
    max_retries: u32,
    /// Rate limit tracker shared across requests.
    pub rate_limiter: RateLimitTracker,
    /// Optional API key rotator for automatic failover on 429.
    pub key_rotator: Option<Arc<KeyRotator>>,
    /// Retry policy with exponential backoff and jitter.
    pub retry_policy: RetryPolicy,
}

impl DeepSeekClient {
    /// Create a new client with the default base URL and timeout.
    pub fn new() -> Self {
        Self::with_config(DEFAULT_BASE_URL, Duration::from_secs(DEFAULT_TIMEOUT_SECS))
    }

    /// Create a new client with a custom base URL.
    pub fn with_base_url(base_url: &str) -> Self {
        Self::with_config(base_url, Duration::from_secs(DEFAULT_TIMEOUT_SECS))
    }

    /// Create a new client with full configuration.
    pub fn with_config(base_url: &str, timeout: Duration) -> Self {
        let client = reqwest::Client::builder()
            .timeout(timeout)
            .build()
            .expect("Failed to build reqwest client");
        Self {
            base_url: base_url.trim_end_matches('/').to_owned(),
            client,
            max_retries: MAX_RETRIES,
            rate_limiter: RateLimitTracker::new(),
            key_rotator: None,
            retry_policy: RetryPolicy::new(),
        }
    }

    /// Create a client from an existing `reqwest::Client`.
    pub fn with_reqwest_client(base_url: &str, client: reqwest::Client) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_owned(),
            client,
            max_retries: MAX_RETRIES,
            rate_limiter: RateLimitTracker::new(),
            key_rotator: None,
            retry_policy: RetryPolicy::new(),
        }
    }

    /// Set the maximum number of retry attempts for transient failures.
    ///
    /// Updates both the legacy field and the [`RetryPolicy`].
    pub fn set_max_retries(&mut self, retries: u32) {
        self.max_retries = retries;
        self.retry_policy.max_retries = retries;
    }

    /// Attach a [`KeyRotator`] for automatic API key failover on 429 errors.
    ///
    /// When set, the client will:
    /// - Mark failing keys as errored in the rotator on 429
    /// - Switch to the next available key from the same pool
    /// - Fall back to the other pool if the current pool is exhausted
    pub fn with_key_rotator(mut self, rotator: Arc<KeyRotator>) -> Self {
        self.key_rotator = Some(rotator);
        self
    }

    /// Override the default [`RetryPolicy`].
    pub fn with_retry_policy(mut self, policy: RetryPolicy) -> Self {
        self.retry_policy = policy;
        self
    }

    /// Attempt to get the next available key from the rotator after a failure.
    ///
    /// Marks the failed key as errored first, then tries Pro pool → Flash pool.
    /// Returns `None` if no rotator is configured or all keys are on cooldown.
    async fn rotate_key(&self, failed_key: &str) -> Option<String> {
        let rotator = self.key_rotator.as_ref()?;
        rotator.mark_error(failed_key, "rate_limit");
        let next = rotator
            .next(Pool::Pro)
            .or_else(|| rotator.next(Pool::Flash));
        if let Some(ref key) = next {
            tracing::info!(
                old_key = %mask_key(failed_key),
                new_key = %mask_key(key),
                "Rotated API key after rate limit"
            );
        }
        next
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Non-streaming chat completion with retry logic.
    ///
    /// Returns the full response text. Automatically retries on transient
    /// failures (timeouts, connection errors, 429 rate limits) with
    /// exponential backoff + jitter. Honors server `Retry-After` headers.
    /// When a [`KeyRotator`] is configured, automatically rotates API keys
    /// on 429 errors.
    pub async fn chat(
        &self,
        messages: &[ChatMessage],
        api_key: &str,
        model: &str,
        temperature: f64,
        max_tokens: u32,
    ) -> AppResult<String> {
        let mut current_key = api_key.to_owned();
        let mut last_error: Option<AppError> = None;

        // Pre-flight rate limit check
        if let Some(wait) =
            RetryPolicy::check_rate_limit(&self.rate_limiter, &current_key, max_tokens)
        {
            tracing::info!(
                key = %mask_key(&current_key),
                wait_secs = wait,
                "Pre-flight: rate limit blocked, waiting"
            );
            tokio::time::sleep(Duration::from_secs_f64(wait)).await;
        }

        for attempt in 0..=self.retry_policy.max_retries {
            if attempt > 0 {
                let backoff = self.retry_policy.backoff(attempt - 1, None);
                tracing::info!(
                    attempt,
                    key = %mask_key(&current_key),
                    backoff_secs = backoff.as_secs_f64(),
                    "LLM: retrying non-stream request"
                );
                tokio::time::sleep(backoff).await;
            }

            match self
                .chat_once(messages, &current_key, model, temperature, max_tokens)
                .await
            {
                Ok(content) => {
                    self.rate_limiter
                        .record_request(&current_key, crate::budget::TokenBudget::estimate(&content) as u32);
                    // Mark key as successful in rotator (clears error count)
                    if let Some(ref rotator) = self.key_rotator {
                        rotator.mark_success(&current_key);
                    }
                    return Ok(content);
                }
                Err((error, retry_after)) => {
                    if !is_retryable(&error) {
                        return Err(error);
                    }
                    tracing::warn!(
                        attempt = attempt + 1,
                        max = self.retry_policy.max_retries + 1,
                        key = %mask_key(&current_key),
                        retry_after = ?retry_after,
                        error = %error,
                        "LLM: request failed, will retry"
                    );

                    // On 429, try rotating the API key
                    if error.code == moling_core::error::ErrorCode::RateLimitExceeded {
                        if let Some(next_key) = self.rotate_key(&current_key).await {
                            tracing::info!(
                                old_key = %mask_key(&current_key),
                                new_key = %mask_key(&next_key),
                                "Switched API key after rate limit"
                            );
                            current_key = next_key;
                        }
                    }

                    // Use Retry-After from server if available for backoff
                    if let Some(delay) = retry_after {
                        let backoff = self.retry_policy.backoff(attempt, Some(delay));
                        tracing::info!(
                            retry_after_secs = delay,
                            backoff_secs = backoff.as_secs_f64(),
                            "Using server Retry-After for backoff"
                        );
                        tokio::time::sleep(backoff).await;
                    }

                    last_error = Some(error);
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            AppError::internal("LLM request failed after all retries".to_owned())
        }))
    }

    /// Streaming chat completion via SSE with retry logic.
    ///
    /// Returns a stream of content deltas. On transient failure, the entire
    /// request is retried up to `max_retries` times. If content has already
    /// been yielded to the caller, the error is propagated immediately
    /// (partial content cannot be retried).
    ///
    /// Honors server `Retry-After` headers and integrates with
    /// [`KeyRotator`](crate::key_rotator::KeyRotator) for automatic
    /// API key failover on 429 errors.
    pub async fn chat_stream(
        &self,
        messages: &[ChatMessage],
        api_key: &str,
        model: &str,
    ) -> AppResult<BoxStream<'static, AppResult<String>>> {
        let mut current_key = api_key.to_owned();
        let mut last_error: Option<AppError> = None;

        for attempt in 0..=self.retry_policy.max_retries {
            if attempt > 0 {
                let backoff = self.retry_policy.backoff(attempt - 1, None);
                tracing::info!(
                    attempt,
                    key = %mask_key(&current_key),
                    backoff_secs = backoff.as_secs_f64(),
                    "LLM: retrying stream request"
                );
                tokio::time::sleep(backoff).await;
            }

            match self.stream_once(messages, &current_key, model).await {
                Ok(stream) => return Ok(stream),
                Err((error, retry_after)) => {
                    if !is_retryable(&error) {
                        return Err(error);
                    }
                    tracing::warn!(
                        attempt = attempt + 1,
                        max = self.retry_policy.max_retries + 1,
                        key = %mask_key(&current_key),
                        retry_after = ?retry_after,
                        error = %error,
                        "LLM: stream request failed, will retry"
                    );

                    // On 429, try rotating the API key
                    if error.code == moling_core::error::ErrorCode::RateLimitExceeded {
                        if let Some(next_key) = self.rotate_key(&current_key).await {
                            current_key = next_key;
                        }
                    }

                    // Use Retry-After from server if available
                    if let Some(delay) = retry_after {
                        let backoff = self.retry_policy.backoff(attempt, Some(delay));
                        tokio::time::sleep(backoff).await;
                    }

                    last_error = Some(error);
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            AppError::internal("LLM stream request failed after all retries".to_owned())
        }))
    }

    // ------------------------------------------------------------------
    // Internal: single-attempt methods
    // ------------------------------------------------------------------

    /// Single non-streaming chat completion (no retry).
    ///
    /// Returns `Ok(content)` on success, or `Err((error, retry_after_secs))` on failure.
    /// The `retry_after_secs` is extracted from the `Retry-After` header on 429 responses.
    async fn chat_once(
        &self,
        messages: &[ChatMessage],
        api_key: &str,
        model: &str,
        temperature: f64,
        max_tokens: u32,
    ) -> Result<String, (AppError, Option<u64>)> {
        let req = ChatRequest {
            model: model.to_owned(),
            messages: messages.to_vec(),
            temperature: Some(temperature),
            max_tokens: Some(max_tokens),
            stream: Some(false),
        };

        let url = format!("{}/v1/chat/completions", self.base_url);
        let resp = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {api_key}"))
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await
            .map_err(|e| {
                let msg = classify_reqwest_error(&e);
                tracing::error!(%url, error = %msg, "LLM: request failed");
                (AppError::internal(format!("LLM request failed: {msg}")), None)
            })?;

        let status = resp.status();
        if !status.is_success() {
            let headers = resp.headers().clone();
            let body = resp.text().await.unwrap_or_default();
            tracing::error!(%status, %body, "LLM: API error");
            return Err(build_error(status.as_u16(), &headers, &body));
        }

        let data: ChatResponse = resp.json().await.map_err(|e| {
            tracing::error!("LLM: deserialize response failed: {e}");
            (AppError::internal("LLM response parse failed".to_owned()), None)
        })?;

        let content = data
            .choices
            .first()
            .and_then(|c| c.message.as_ref())
            .map(|m| m.content.clone())
            .unwrap_or_default();

        Ok(content)
    }

    /// Single streaming chat completion via SSE (no retry).
    ///
    /// Returns `Ok(stream)` on success, or `Err((error, retry_after_secs))` on failure.
    async fn stream_once(
        &self,
        messages: &[ChatMessage],
        api_key: &str,
        model: &str,
    ) -> Result<BoxStream<'static, AppResult<String>>, (AppError, Option<u64>)> {
        let req = ChatRequest {
            model: model.to_owned(),
            messages: messages.to_vec(),
            temperature: None,
            max_tokens: None,
            stream: Some(true),
        };

        let url = format!("{}/v1/chat/completions", self.base_url);
        let resp = self
            .client
            .post(&url)
            .header("Authorization", format!("Bearer {api_key}"))
            .header("Content-Type", "application/json")
            .json(&req)
            .send()
            .await
            .map_err(|e| {
                let msg = classify_reqwest_error(&e);
                tracing::error!(%url, error = %msg, "LLM: stream request failed");
                (AppError::internal(format!("LLM stream request failed: {msg}")), None)
            })?;

        let status = resp.status();
        if !status.is_success() {
            let headers = resp.headers().clone();
            let body = resp.text().await.unwrap_or_default();
            tracing::error!(%status, %body, "LLM: stream API error");
            return Err(build_error(status.as_u16(), &headers, &body));
        }

        let stream = resp
            .bytes_stream()
            .map(|chunk| -> AppResult<String> {
                let bytes = chunk.map_err(|e| {
                    AppError::internal(format!("Stream read error: {e}"))
                })?;
                let text = String::from_utf8_lossy(&bytes);
                let mut content = String::new();
                for line in text.lines() {
                    if let Some(data) = line.strip_prefix("data: ") {
                        if data == "[DONE]" {
                            continue;
                        }
                        if let Ok(resp) = serde_json::from_str::<ChatResponse>(data) {
                            if let Some(delta) =
                                resp.choices.first().and_then(|c| c.delta.as_ref())
                            {
                                if let Some(c) = &delta.content {
                                    content.push_str(c);
                                }
                            }
                        }
                    }
                }
                Ok(content)
            });

        Ok(Box::pin(stream))
    }
}

impl Default for DeepSeekClient {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Classify a `reqwest::Error` into a human-readable message for logging.
fn classify_reqwest_error(e: &reqwest::Error) -> String {
    if e.is_timeout() {
        "request timeout".to_owned()
    } else if e.is_connect() {
        "connection error".to_owned()
    } else if e.is_request() {
        "request build error".to_owned()
    } else if e.is_body() {
        "request body error".to_owned()
    } else if e.is_decode() {
        "response decode error".to_owned()
    } else {
        format!("{e}")
    }
}

/// Mask an API key, showing only the first 10 characters.
pub(crate) fn mask_key(key: &str) -> String {
    if key.len() > 10 {
        format!("{}...", &key[..10])
    } else {
        key.to_owned()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_client_construction() {
        let client = DeepSeekClient::new();
        assert!(client.base_url.contains("deepseek"));
    }

    #[test]
    fn test_client_custom_url() {
        let client = DeepSeekClient::with_base_url("https://custom.api.com/v1");
        assert_eq!(client.base_url, "https://custom.api.com/v1");
    }

    #[test]
    fn test_chat_message_serialize() {
        let msg = ChatMessage {
            role: "user".into(),
            content: "Hello".into(),
        };
        let json = serde_json::to_string(&msg).unwrap();
        assert!(json.contains("Hello"));
    }

    #[test]
    fn test_chat_message_constructors() {
        let sys = ChatMessage::system("system prompt");
        assert_eq!(sys.role, "system");
        let user = ChatMessage::user("hello");
        assert_eq!(user.role, "user");
        let asst = ChatMessage::assistant("response");
        assert_eq!(asst.role, "assistant");
    }

    #[test]
    fn test_is_retryable() {
        assert!(is_retryable(&AppError::internal("timeout".to_owned())));
        assert!(is_retryable(&AppError::internal("connection reset".to_owned())));
        assert!(!is_retryable(&AppError::internal("invalid api key".to_owned())));
    }

    #[test]
    fn test_rate_limit_tracker_default() {
        let tracker = RateLimitTracker::new();
        assert!(tracker.can_make_request("test-key", 1000));
    }

    #[test]
    fn test_rate_limit_tracker_recording() {
        let tracker = RateLimitTracker::new();
        tracker.record_request("test-key", 500);
        assert!(tracker.can_make_request("test-key", 1000));
    }

    #[test]
    fn test_mask_key() {
        assert_eq!(mask_key("sk-abcdefghijklmn"), "sk-abcdefg...");
        assert_eq!(mask_key("short"), "short");
    }

    #[test]
    fn test_build_error_429() {
        let headers = reqwest::header::HeaderMap::new();
        let (err, retry_after) = build_error(
            429,
            &headers,
            r#"{"error":{"message":"Rate limit exceeded","code":"rate_limit_exceeded"}}"#,
        );
        assert_eq!(err.code, moling_core::error::ErrorCode::RateLimitExceeded);
        assert_eq!(retry_after, None);
    }

    #[test]
    fn test_build_error_429_with_retry_after() {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::RETRY_AFTER,
            "15".parse().unwrap(),
        );
        let (err, retry_after) = build_error(
            429,
            &headers,
            r#"{"error":{"message":"Rate limit exceeded"}}"#,
        );
        assert_eq!(err.code, moling_core::error::ErrorCode::RateLimitExceeded);
        assert_eq!(retry_after, Some(15));
    }

    #[test]
    fn test_build_error_500() {
        let headers = reqwest::header::HeaderMap::new();
        let (err, retry_after) = build_error(500, &headers, r#"{"error":{"message":"Internal error"}}"#);
        assert_eq!(err.code, moling_core::error::ErrorCode::InternalError);
        assert_eq!(retry_after, None);
    }

    #[test]
    fn test_classify_reqwest_error_timeout() {
        // Create a timeout error indirectly
        let client = reqwest::Client::new();
        let rt = tokio::runtime::Runtime::new().unwrap();
        let result = rt.block_on(async {
            client
                .get("http://0.0.0.0:1")
                .timeout(Duration::from_millis(1))
                .send()
                .await
        });
        if let Err(e) = result {
            let msg = classify_reqwest_error(&e);
            // Either timeout or connect error is acceptable for an unreachable address
            assert!(
                msg.contains("timeout")
                    || msg.contains("connect")
                    || msg.contains("error"),
                "Got: {msg}"
            );
        }
    }
}
