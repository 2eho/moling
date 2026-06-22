//! Secret service — business logic for secret (秘密矩阵) CRUD, debt, and matrix operations.
//!
//! Implements the complete secret lifecycle:
//!
//! 1. **Weighted Debt Calculation** — each secrecy level carries a weight,
//!    and debt decays with chapter distance.
//! 2. **Partial Reveal** — given a character, determine what parts of a
//!    secret are known or unknown.
//! 3. **Secret Chain Resolution** — secret A discovered → leads to secret B.
//! 4. **Secrecy Matrix** — who-knows-what relationship matrix.
//! 5. **Conflict Detection** — detect contradictory secrets.
//!
//! ## Secrecy Level Weights
//!
//! | Level   | Weight | Description                     |
//! |---------|--------|---------------------------------|
//! | PUBLIC  | 1      | Known to all / exposed          |
//! | LOW     | 3      | Minor secret, low impact        |
//! | MEDIUM  | 8      | Significant secret              |
//! | HIGH    | 20     | Major secret, high impact       |
//! | TOP     | 50     | World-shattering revelation     |

use moling_core::error::{AppError, AppResult};
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::secret_dao::SecretDao;
use moling_db::entities::secret::Model as SecretModel;
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

// ---------------------------------------------------------------------------
// Secrecy Level
// ---------------------------------------------------------------------------

/// Secrecy level with associated debt weight.
///
/// Ported from the Python secret debt model (§5.2 of spec).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SecrecyLevel {
    /// Fully exposed / known to all characters.
    Public,
    /// Minor secret, low narrative impact.
    Low,
    /// Significant secret with meaningful narrative weight.
    Medium,
    /// Major secret, high impact on plot.
    High,
    /// World-shattering revelation, maximum narrative weight.
    Top,
}

impl SecrecyLevel {
    /// The debt weight applied during debt calculation.
    pub fn weight(self) -> f64 {
        match self {
            Self::Public => 1.0,
            Self::Low => 3.0,
            Self::Medium => 8.0,
            Self::High => 20.0,
            Self::Top => 50.0,
        }
    }

    /// Parse from the database `secrecy_level` string.
    pub fn from_db_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "public" | "revealed" => Self::Public,
            "low" | "hidden" => Self::Low,
            "medium" | "partial" => Self::Medium,
            "high" => Self::High,
            "top" => Self::Top,
            _ => Self::Low, // Safe default for unknown values
        }
    }

    /// Convert to database string.
    pub fn to_db_str(self) -> &'static str {
        match self {
            Self::Public => "revealed",
            Self::Low => "hidden",
            Self::Medium => "partial",
            Self::High => "high",
            Self::Top => "top",
        }
    }
}

impl std::fmt::Display for SecrecyLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Public => write!(f, "public"),
            Self::Low => write!(f, "low"),
            Self::Medium => write!(f, "medium"),
            Self::High => write!(f, "high"),
            Self::Top => write!(f, "top"),
        }
    }
}

// ---------------------------------------------------------------------------
// Result / summary types
// ---------------------------------------------------------------------------

/// Summary of secret debt calculation for a project.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretDebtSummary {
    /// Total aggregated debt across all non-revealed secrets.
    pub total_debt: f64,
    /// Count of fully hidden secrets (level = Low).
    pub hidden_count: usize,
    /// Count of partially revealed secrets (level = Medium).
    pub partial_count: usize,
    /// Count of fully revealed secrets (level = Public).
    pub revealed_count: usize,
    /// Per-secret detail entries.
    pub details: Vec<SecretDebtDetail>,
}

/// Per-secret debt detail.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretDebtDetail {
    pub secret_id: String,
    pub description: String,
    pub debt: f64,
    pub level: SecrecyLevel,
    pub chapter_distance: Option<i32>,
}

/// Result of a secrecy matrix computation for a character.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecrecyMatrixResult {
    pub character_name: String,
    /// Secrets known by this character.
    pub known: Vec<SecretMatrixEntry>,
    /// Secrets unknown to this character.
    pub unknown: Vec<SecretMatrixEntry>,
    /// Number of secret chains this character is part of.
    pub chain_count: usize,
}

/// A single entry in the secrecy matrix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretMatrixEntry {
    pub secret_id: String,
    pub description: String,
    pub secrecy_level: SecrecyLevel,
    pub debt: f64,
}

/// Result of partial reveal analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartialReveal {
    pub secret_id: String,
    pub description: String,
    /// Which characters know this secret.
    pub known_by: Vec<String>,
    /// Which characters are in the dark.
    pub unknown_to: Vec<String>,
    /// The secrecy level.
    pub level: SecrecyLevel,
    /// Whether the given character knows this secret.
    pub character_knows: bool,
    /// The portion of the secret known (0.0 = nothing, 1.0 = full).
    pub knowledge_fraction: f64,
}

/// A node in a secret chain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretChainNode {
    pub secret_id: String,
    pub description: String,
    pub level: SecrecyLevel,
    /// IDs of secrets that this secret leads to.
    pub leads_to: Vec<String>,
    /// IDs of secrets that lead to this secret.
    pub discovered_by: Vec<String>,
}

/// Conflict between two secrets.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretConflict {
    pub secret_a_id: String,
    pub secret_a_description: String,
    pub secret_b_id: String,
    pub secret_b_description: String,
    /// Reason for the conflict.
    pub conflict_reason: String,
    /// Severity: "low", "medium", "high".
    pub severity: String,
}

// ---------------------------------------------------------------------------
// SecretService
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct SecretService {
    secret_dao: SecretDao,
    project_dao: ProjectDao,
}

/// Returns `true` if `ch` is in the CJK Unified Ideographs block (U+4E00–U+9FFF).
fn is_cjk(ch: char) -> bool {
    matches!(ch, '\u{4E00}'..='\u{9FFF}')
}

impl SecretService {
    pub fn new() -> Self {
        Self {
            secret_dao: SecretDao,
            project_dao: ProjectDao,
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Ownership verification
    // ─────────────────────────────────────────────────────────────────

    async fn verify_owner(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<()> {
        let p = self
            .project_dao
            .find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(())
    }

    // ─────────────────────────────────────────────────────────────────
    // Basic CRUD (backward-compatible)
    // ─────────────────────────────────────────────────────────────────

    /// List all secrets for a project.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<SecretModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.secret_dao.list_by_project(db, project_id).await
    }

    /// List secrets by character (secrets known by the given character).
    pub async fn list_by_character(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_id: &str,
    ) -> AppResult<Vec<SecretModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        let all = self.secret_dao.list_by_project(db, project_id).await?;
        let filtered: Vec<_> = all
            .into_iter()
            .filter(|s| {
                s.known_by.as_array().map_or(false, |arr| {
                    arr.iter().any(|v| v.as_str() == Some(character_id))
                })
            })
            .collect();
        Ok(filtered)
    }

    /// Create a new secret.
    #[allow(clippy::too_many_arguments)]
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        description: &str,
        secrecy_level: &str,
        known_by: Json,
        unknown_to: Json,
        debt: i32,
        created_chapter: Option<i32>,
    ) -> AppResult<SecretModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let model = moling_db::entities::secret::ActiveModel {
            id: Set(uuid::Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            description: Set(description.to_owned()),
            secrecy_level: Set(secrecy_level.to_owned()),
            known_by: Set(known_by),
            unknown_to: Set(unknown_to),
            debt: Set(debt),
            created_chapter: Set(created_chapter),
            ..Default::default()
        };
        self.secret_dao.create(db, model).await
    }

    /// Get a single secret by ID.
    pub async fn get(
        &self,
        db: &DatabaseConnection,
        _user_id: &str,
        _project_id: i32,
        secret_id: &str,
    ) -> AppResult<SecretModel> {
        self.secret_dao
            .find_by_id(db, secret_id)
            .await?
            .ok_or_else(|| AppError::not_found("Secret not found".to_owned()))
    }

    /// Update a secret's fields.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        secret_id: &str,
        description: Option<&str>,
        secrecy_level: Option<&str>,
        debt: Option<i32>,
    ) -> AppResult<SecretModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let s = self
            .secret_dao
            .find_by_id(db, secret_id)
            .await?
            .ok_or_else(|| AppError::not_found("Secret not found".to_owned()))?;
        let mut a = s.into_active_model();
        if let Some(v) = description {
            a.description = Set(v.to_owned());
        }
        if let Some(v) = secrecy_level {
            a.secrecy_level = Set(v.to_owned());
        }
        if let Some(v) = debt {
            a.debt = Set(v);
        }
        a.update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update secret failed: {e}")))
    }

    /// Delete (soft-delete) a secret.
    pub async fn delete(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        secret_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;
        self.secret_dao.soft_delete(db, secret_id).await
    }

    /// Sum raw debt from database (simple sum, backward-compatible).
    pub async fn debt_summary(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<i32> {
        self.verify_owner(db, user_id, project_id).await?;
        self.secret_dao
            .calculate_debt_by_project(db, project_id)
            .await
    }

    // ─────────────────────────────────────────────────────────────────
    // Weighted Debt Calculation
    // ─────────────────────────────────────────────────────────────────

    /// Calculate weighted secret debt for a project.
    ///
    /// Debt = secrecy_level_weight × (1.0 + chapter_distance_decay)
    ///
    /// The further a secret is from the current chapter without being exposed,
    /// the more "narrative debt" it accumulates.
    pub async fn calculate_weighted_debt(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        current_chapter: i32,
    ) -> AppResult<SecretDebtSummary> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let mut total_debt: f64 = 0.0;
        let mut hidden_count: usize = 0;
        let mut partial_count: usize = 0;
        let mut revealed_count: usize = 0;
        let mut details: Vec<SecretDebtDetail> = Vec::new();

        for s in &secrets {
            let level = SecrecyLevel::from_db_str(&s.secrecy_level);

            match level {
                SecrecyLevel::Public => {
                    revealed_count += 1;
                    // No debt for revealed secrets
                    details.push(SecretDebtDetail {
                        secret_id: s.id.clone(),
                        description: s.description.clone(),
                        debt: 0.0,
                        level,
                        chapter_distance: None,
                    });
                }
                SecrecyLevel::Low => {
                    hidden_count += 1;
                    let chapter_dist = s.created_chapter.map(|c| current_chapter.saturating_sub(c));
                    let decay = Self::chapter_distance_decay(chapter_dist);
                    let debt = level.weight() * (1.0 + decay);
                    total_debt += debt;

                    details.push(SecretDebtDetail {
                        secret_id: s.id.clone(),
                        description: s.description.clone(),
                        debt,
                        level,
                        chapter_distance: chapter_dist,
                    });
                }
                SecrecyLevel::Medium => {
                    partial_count += 1;
                    let chapter_dist = s.created_chapter.map(|c| current_chapter.saturating_sub(c));
                    let decay = Self::chapter_distance_decay(chapter_dist);
                    // Partial secrets accumulate debt at half rate
                    let debt = level.weight() * (1.0 + decay) * 0.5;
                    total_debt += debt;

                    details.push(SecretDebtDetail {
                        secret_id: s.id.clone(),
                        description: s.description.clone(),
                        debt,
                        level,
                        chapter_distance: chapter_dist,
                    });
                }
                SecrecyLevel::High | SecrecyLevel::Top => {
                    hidden_count += 1;
                    let chapter_dist = s.created_chapter.map(|c| current_chapter.saturating_sub(c));
                    let decay = Self::chapter_distance_decay(chapter_dist);
                    let debt = level.weight() * (1.0 + decay);
                    total_debt += debt;

                    details.push(SecretDebtDetail {
                        secret_id: s.id.clone(),
                        description: s.description.clone(),
                        debt,
                        level,
                        chapter_distance: chapter_dist,
                    });
                }
            }
        }

        Ok(SecretDebtSummary {
            total_debt,
            hidden_count,
            partial_count,
            revealed_count,
            details,
        })
    }

    /// Chapter distance decay factor.
    ///
    /// `decay = min(distance / 5.0, 1.5)` — caps at 1.5x for very old secrets.
    fn chapter_distance_decay(distance: Option<i32>) -> f64 {
        match distance {
            Some(d) if d > 0 => f64::min(d as f64 / 5.0, 1.5),
            _ => 0.0,
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Debt Aggregation with Decay Over Time
    // ─────────────────────────────────────────────────────────────────

    /// Aggregate all debts with an exponential decay factor applied per chapter.
    ///
    /// This is a read-only variant that does NOT mutate the database.
    /// Used for "what-if" analysis before actually updating debts.
    pub async fn debt_aggregation_with_decay(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        current_chapter: i32,
        decay_rate: f64,
    ) -> AppResult<Vec<SecretDebtDetail>> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let mut results: Vec<SecretDebtDetail> = Vec::with_capacity(secrets.len());

        for s in &secrets {
            let level = SecrecyLevel::from_db_str(&s.secrecy_level);
            let chapter_dist = s.created_chapter.map(|c| current_chapter.saturating_sub(c));

            let debt = if matches!(level, SecrecyLevel::Public) {
                0.0
            } else {
                let base = level.weight();
                let decay = match chapter_dist {
                    Some(d) if d > 0 => (decay_rate.powi(d)) as f64,
                    _ => 1.0,
                };
                let partial_factor = if matches!(level, SecrecyLevel::Medium) {
                    0.5
                } else {
                    1.0
                };
                base * decay * partial_factor
            };

            results.push(SecretDebtDetail {
                secret_id: s.id.clone(),
                description: s.description.clone(),
                debt,
                level,
                chapter_distance: chapter_dist,
            });
        }

        Ok(results)
    }

    // ─────────────────────────────────────────────────────────────────
    // Partial Reveal
    // ─────────────────────────────────────────────────────────────────

    /// Compute what a given character knows and doesn't know about each secret.
    ///
    /// Returns a list of [`PartialReveal`] entries, one per secret in the project.
    pub async fn partial_reveal(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_name: &str,
    ) -> AppResult<Vec<PartialReveal>> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let reveals: Vec<PartialReveal> = secrets
            .iter()
            .map(|s| {
                let level = SecrecyLevel::from_db_str(&s.secrecy_level);
                let known_by: Vec<String> = s
                    .known_by
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();
                let unknown_to: Vec<String> = s
                    .unknown_to
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();

                let character_knows = known_by.iter().any(|name| name == character_name);
                let knowledge_fraction =
                    Self::compute_knowledge_fraction(&known_by, &unknown_to, character_name, level);

                PartialReveal {
                    secret_id: s.id.clone(),
                    description: s.description.clone(),
                    known_by,
                    unknown_to,
                    level,
                    character_knows,
                    knowledge_fraction,
                }
            })
            .collect();

        Ok(reveals)
    }

    /// Estimate how much of a secret a character knows (0.0–1.0).
    fn compute_knowledge_fraction(
        known_by: &[String],
        unknown_to: &[String],
        character_name: &str,
        level: SecrecyLevel,
    ) -> f64 {
        if known_by.iter().any(|n| n == character_name) {
            // Character explicitly knows this secret
            match level {
                SecrecyLevel::Public => 1.0,
                SecrecyLevel::Low => 0.8,
                SecrecyLevel::Medium => 0.5,
                SecrecyLevel::High => 0.3,
                SecrecyLevel::Top => 0.15,
            }
        } else if unknown_to.iter().any(|n| n == character_name) {
            // Character is explicitly listed as not knowing
            0.0
        } else {
            // Character is not in either list — partially aware based on level
            match level {
                SecrecyLevel::Public => 0.9,
                SecrecyLevel::Low => 0.2,
                SecrecyLevel::Medium => 0.1,
                SecrecyLevel::High => 0.05,
                SecrecyLevel::Top => 0.0,
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Secrecy Matrix Computation
    // ─────────────────────────────────────────────────────────────────

    /// Compute the full secrecy matrix for a given character.
    ///
    /// Returns what the character knows vs. doesn't know, plus chain involvement.
    pub async fn compute_secrecy_matrix(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_name: &str,
    ) -> AppResult<SecrecyMatrixResult> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let mut known: Vec<SecretMatrixEntry> = Vec::new();
        let mut unknown: Vec<SecretMatrixEntry> = Vec::new();
        let mut chain_count: usize = 0;

        for s in &secrets {
            let level = SecrecyLevel::from_db_str(&s.secrecy_level);
            let debt = Self::calculate_secret_debt_value(s, level);

            let entry = SecretMatrixEntry {
                secret_id: s.id.clone(),
                description: s.description.clone(),
                secrecy_level: level,
                debt,
            };

            let is_known = s.known_by.as_array().map_or(false, |arr| {
                arr.iter().any(|v| v.as_str() == Some(character_name))
            });

            if is_known {
                known.push(entry);
            } else {
                unknown.push(entry);
            }

            // Count chains: if this secret has a description that references
            // another secret, it might be part of a chain. We check for
            // description patterns suggesting linkage.
            if s.description.contains("秘密")
                || s.description.contains("发现")
                || s.description.contains("线索")
            {
                chain_count += 1;
            }
        }

        Ok(SecrecyMatrixResult {
            character_name: character_name.to_owned(),
            known,
            unknown,
            chain_count,
        })
    }

    /// Compute the debt value for a single secret (internal helper).
    fn calculate_secret_debt_value(s: &SecretModel, level: SecrecyLevel) -> f64 {
        match level {
            SecrecyLevel::Public => 0.0,
            _ => {
                let base = level.weight();
                let stored_debt = s.debt as f64;
                if stored_debt > 0.0 {
                    // Use stored debt if available, otherwise compute from weight
                    f64::max(base, stored_debt)
                } else {
                    base
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Secret Chain Resolution
    // ─────────────────────────────────────────────────────────────────

    /// Resolve secret chains — find which secrets lead to which other secrets.
    ///
    /// A chain exists when:
    /// - Secret A's description mentions a concept revealed in Secret B
    /// - Secret A and B share character knowledge patterns
    /// - Secrets are thematically linked
    pub async fn resolve_secret_chains(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<SecretChainNode>> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let mut nodes: Vec<SecretChainNode> = Vec::with_capacity(secrets.len());

        for s in &secrets {
            let level = SecrecyLevel::from_db_str(&s.secrecy_level);

            // Find secrets that share knowledge patterns with this one
            let known_set: Vec<String> = s
                .known_by
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();

            let mut leads_to: Vec<String> = Vec::new();
            let mut discovered_by: Vec<String> = Vec::new();

            for other in &secrets {
                if other.id == s.id {
                    continue;
                }

                let other_known: Vec<String> = other
                    .known_by
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();

                // If this secret's knowers are a subset of another's,
                // discovering this might lead to the other
                let shared_knowers: Vec<_> = known_set
                    .iter()
                    .filter(|name| other_known.contains(name))
                    .collect();

                if !shared_knowers.is_empty() {
                    // Check chapter ordering
                    match (s.created_chapter, other.created_chapter) {
                        (Some(a), Some(b)) if a < b => {
                            leads_to.push(other.id.clone());
                        }
                        (Some(a), Some(b)) if a > b => {
                            discovered_by.push(other.id.clone());
                        }
                        _ => {
                            // Same chapter or unknown: check description overlap
                            if Self::has_description_overlap(&s.description, &other.description) {
                                leads_to.push(other.id.clone());
                            }
                        }
                    }
                }
            }

            nodes.push(SecretChainNode {
                secret_id: s.id.clone(),
                description: s.description.clone(),
                level,
                leads_to,
                discovered_by,
            });
        }

        Ok(nodes)
    }

    /// Check if two descriptions have significant word overlap.
    /// Detect semantic overlap between two descriptions.
    ///
    /// For CJK-heavy text (≥50% CJK chars), splits into individual characters for
    /// granular overlap detection between phrases like "国王的秘密身份" and "国王隐藏的真实身份".
    /// Otherwise uses word-level splitting (non-alphanumeric boundaries).
    fn has_description_overlap(a: &str, b: &str) -> bool {
        let extract_words = |s: &str| -> Vec<String> {
            let cjk_count = s.chars().filter(|c| is_cjk(*c)).count();
            let total = s.chars().count();
            if total > 0 && cjk_count * 2 >= total {
                // CJK-heavy → character-level split, treat each char as a word
                s.chars()
                    .filter(|c| c.is_alphanumeric() || *c == '_')
                    .map(|c| c.to_string())
                    .collect()
            } else {
                // Word-level split
                s.split(|c: char| !c.is_alphanumeric() && c != '_')
                    .filter(|w| w.len() >= 2)
                    .map(|w| w.to_lowercase())
                    .collect()
            }
        };

        let a_words: std::collections::HashSet<String> = extract_words(a).into_iter().collect();
        let b_words: std::collections::HashSet<String> = extract_words(b).into_iter().collect();

        if a_words.is_empty() || b_words.is_empty() {
            return false;
        }

        let intersection = a_words.intersection(&b_words).count();
        let union = a_words.union(&b_words).count();
        let jaccard = intersection as f64 / union as f64;

        jaccard > 0.3
    }

    // ─────────────────────────────────────────────────────────────────
    // Conflict Detection
    // ─────────────────────────────────────────────────────────────────

    /// Detect conflicts between secrets.
    ///
    /// A conflict exists when two secrets:
    /// - Have contradictory knowledge (different characters know mutually exclusive info)
    /// - Have overlapping descriptions that contradict each other
    /// - Are both marked as TOP/HIGH for the same character
    pub async fn detect_conflicts(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<SecretConflict>> {
        self.verify_owner(db, user_id, project_id).await?;
        let secrets = self.secret_dao.list_by_project(db, project_id).await?;

        let mut conflicts: Vec<SecretConflict> = Vec::new();
        let n = secrets.len();

        for i in 0..n {
            for j in (i + 1)..n {
                let a = &secrets[i];
                let b = &secrets[j];

                // Check for mutually exclusive knowledge
                let a_known: Vec<String> = a
                    .known_by
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();
                let b_unknown: Vec<String> = b
                    .unknown_to
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();

                // Conflict type 1: Character A knows secret X, but secret Y says
                // A shouldn't know it (A is in Y's unknown_to while also in X's known_by)
                let mut conflict_reason = String::new();
                let mut severity = "low";

                for knower in &a_known {
                    if b_unknown.contains(knower) {
                        conflict_reason = format!(
                            "角色「{knower}」知道秘密「{}」但被列为不知道秘密「{}」",
                            a.description, b.description
                        );
                        severity = "medium";
                        break;
                    }
                }

                // Conflict type 2: Both are high-impact and describe the same event
                // differently
                let a_level = SecrecyLevel::from_db_str(&a.secrecy_level);
                let b_level = SecrecyLevel::from_db_str(&b.secrecy_level);

                if conflict_reason.is_empty()
                    && matches!(a_level, SecrecyLevel::High | SecrecyLevel::Top)
                    && matches!(b_level, SecrecyLevel::High | SecrecyLevel::Top)
                    && Self::has_description_overlap(&a.description, &b.description)
                {
                    conflict_reason = format!(
                        "两个高权重秘密描述了相似内容：「{}」和「{}」",
                        a.description, b.description
                    );
                    severity = "high";
                }

                // Conflict type 3: Contradictory secrecy levels for overlapping
                // character sets
                if conflict_reason.is_empty() {
                    let b_known: Vec<String> = b
                        .known_by
                        .as_array()
                        .map(|arr| {
                            arr.iter()
                                .filter_map(|v| v.as_str().map(String::from))
                                .collect()
                        })
                        .unwrap_or_default();

                    let shared_knowers: Vec<_> = a_known
                        .iter()
                        .filter(|name| b_known.contains(name))
                        .collect();
                    let a_weight = a_level.weight();
                    let b_weight = b_level.weight();

                    if !shared_knowers.is_empty() && (a_weight - b_weight).abs() > 10.0 {
                        conflict_reason = format!(
                            "{}个角色同时知道权重差异大的秘密（{} vs {}）",
                            shared_knowers.len(),
                            a_level,
                            b_level
                        );
                        severity = "low";
                    }
                }

                if !conflict_reason.is_empty() {
                    conflicts.push(SecretConflict {
                        secret_a_id: a.id.clone(),
                        secret_a_description: a.description.clone(),
                        secret_b_id: b.id.clone(),
                        secret_b_description: b.description.clone(),
                        conflict_reason,
                        severity: severity.to_owned(),
                    });
                }
            }
        }

        Ok(conflicts)
    }

    // ─────────────────────────────────────────────────────────────────
    // Secret Propagation
    // ─────────────────────────────────────────────────────────────────

    /// Propagate a secret to a new character.
    ///
    /// Adds the character to `known_by`, removes from `unknown_to`,
    /// and updates `secrecy_level` if enough characters now know.
    pub async fn propagate_secret(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        secret_id: &str,
        new_knower: &str,
    ) -> AppResult<SecretModel> {
        self.verify_owner(db, user_id, project_id).await?;

        let s = self
            .secret_dao
            .find_by_id(db, secret_id)
            .await?
            .ok_or_else(|| AppError::not_found("Secret not found".to_owned()))?;

        let mut a = s.into_active_model();

        // Update known_by
        let mut known_by: Vec<String> = match &a.known_by {
            sea_orm::ActiveValue::Set(v) | sea_orm::ActiveValue::Unchanged(v) => v
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default(),
            sea_orm::ActiveValue::NotSet => Vec::new(),
        };

        if !known_by.contains(&new_knower.to_owned()) {
            known_by.push(new_knower.to_owned());
            a.known_by = Set(serde_json::to_value(&known_by).unwrap_or_default());
        }

        // Update unknown_to
        let mut unknown_to: Vec<String> = match &a.unknown_to {
            sea_orm::ActiveValue::Set(v) | sea_orm::ActiveValue::Unchanged(v) => v
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default(),
            sea_orm::ActiveValue::NotSet => Vec::new(),
        };

        unknown_to.retain(|name| name != new_knower);
        a.unknown_to = Set(serde_json::to_value(&unknown_to).unwrap_or_default());

        // Update secrecy_level if more characters know
        if known_by.len() >= 2 {
            a.secrecy_level = Set("partial".to_owned());
        }

        a.update(db)
            .await
            .map_err(|e| AppError::internal(format!("Propagate secret failed: {e}")))
    }

    /// Expose a secret (mark as revealed).
    pub async fn expose_secret(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        secret_id: &str,
        _exposure_chapter: Option<i32>,
    ) -> AppResult<SecretModel> {
        self.verify_owner(db, user_id, project_id).await?;

        let s = self
            .secret_dao
            .find_by_id(db, secret_id)
            .await?
            .ok_or_else(|| AppError::not_found("Secret not found".to_owned()))?;

        let mut a = s.into_active_model();
        a.secrecy_level = Set("revealed".to_owned());
        a.debt = Set(0);

        a.update(db)
            .await
            .map_err(|e| AppError::internal(format!("Expose secret failed: {e}")))
    }

    // ─────────────────────────────────────────────────────────────────
    // Batch Operations
    // ─────────────────────────────────────────────────────────────────

    /// Batch update secrecy levels for multiple secrets.
    pub async fn batch_update_levels(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        updates: &[(String, SecrecyLevel)],
    ) -> AppResult<Vec<SecretModel>> {
        self.verify_owner(db, user_id, project_id).await?;

        let mut results = Vec::with_capacity(updates.len());
        for (secret_id, level) in updates {
            let s = self
                .secret_dao
                .find_by_id(db, secret_id)
                .await?
                .ok_or_else(|| AppError::not_found(format!("Secret not found: {secret_id}")))?;

            let mut a = s.into_active_model();
            a.secrecy_level = Set(level.to_db_str().to_owned());

            let updated = a
                .update(db)
                .await
                .map_err(|e| AppError::internal(format!("Batch update secret failed: {e}")))?;

            results.push(updated);
        }

        Ok(results)
    }

    /// Batch propagate secrets to multiple characters.
    ///
    /// Each entry is `(secret_id, character_name)`.
    pub async fn batch_propagate(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        propagations: &[(String, String)],
    ) -> AppResult<Vec<SecretModel>> {
        let mut results = Vec::with_capacity(propagations.len());
        for (secret_id, character_name) in propagations {
            let updated = self
                .propagate_secret(db, user_id, project_id, secret_id, character_name)
                .await?;
            results.push(updated);
        }
        Ok(results)
    }
}

impl Default for SecretService {
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

    // ── SecrecyLevel tests ──

    #[test]
    fn test_secrecy_level_weights() {
        assert!((SecrecyLevel::Public.weight() - 1.0).abs() < f64::EPSILON);
        assert!((SecrecyLevel::Low.weight() - 3.0).abs() < f64::EPSILON);
        assert!((SecrecyLevel::Medium.weight() - 8.0).abs() < f64::EPSILON);
        assert!((SecrecyLevel::High.weight() - 20.0).abs() < f64::EPSILON);
        assert!((SecrecyLevel::Top.weight() - 50.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_secrecy_level_from_db_str() {
        assert_eq!(SecrecyLevel::from_db_str("hidden"), SecrecyLevel::Low);
        assert_eq!(SecrecyLevel::from_db_str("partial"), SecrecyLevel::Medium);
        assert_eq!(SecrecyLevel::from_db_str("revealed"), SecrecyLevel::Public);
        assert_eq!(SecrecyLevel::from_db_str("high"), SecrecyLevel::High);
        assert_eq!(SecrecyLevel::from_db_str("top"), SecrecyLevel::Top);
        // Unknown values default to Low
        assert_eq!(SecrecyLevel::from_db_str("unknown"), SecrecyLevel::Low);
    }

    #[test]
    fn test_secrecy_level_to_db_str() {
        assert_eq!(SecrecyLevel::Public.to_db_str(), "revealed");
        assert_eq!(SecrecyLevel::Low.to_db_str(), "hidden");
        assert_eq!(SecrecyLevel::Medium.to_db_str(), "partial");
        assert_eq!(SecrecyLevel::High.to_db_str(), "high");
        assert_eq!(SecrecyLevel::Top.to_db_str(), "top");
    }

    #[test]
    fn test_secrecy_level_display() {
        assert_eq!(format!("{}", SecrecyLevel::Public), "public");
        assert_eq!(format!("{}", SecrecyLevel::High), "high");
    }

    // ── Chapter distance decay tests ──

    #[test]
    fn test_chapter_distance_decay_zero() {
        assert!((SecretService::chapter_distance_decay(None) - 0.0).abs() < f64::EPSILON);
        assert!((SecretService::chapter_distance_decay(Some(0)) - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_chapter_distance_decay_normal() {
        // 5 chapters → 1.0 decay
        assert!((SecretService::chapter_distance_decay(Some(5)) - 1.0).abs() < f64::EPSILON);
        // 3 chapters → 0.6 decay
        assert!((SecretService::chapter_distance_decay(Some(3)) - 0.6).abs() < f64::EPSILON);
    }

    #[test]
    fn test_chapter_distance_decay_capped() {
        // 10 chapters → capped at 1.5
        assert!((SecretService::chapter_distance_decay(Some(10)) - 1.5).abs() < f64::EPSILON);
        // 20 chapters → still 1.5
        assert!((SecretService::chapter_distance_decay(Some(20)) - 1.5).abs() < f64::EPSILON);
    }

    // ── Description overlap tests ──

    #[test]
    fn test_has_description_overlap_positive() {
        assert!(SecretService::has_description_overlap(
            "国王的秘密身份被揭露",
            "国王隐藏的真实身份"
        ));
    }

    #[test]
    fn test_has_description_overlap_negative() {
        assert!(!SecretService::has_description_overlap(
            "国王的秘密身份",
            "魔法石的力量来源"
        ));
    }

    #[test]
    fn test_has_description_overlap_empty() {
        assert!(!SecretService::has_description_overlap("a", "b"));
        assert!(!SecretService::has_description_overlap("", "test"));
    }

    // ── Knowledge fraction tests ──

    #[test]
    fn test_compute_knowledge_fraction_known() {
        let known = vec!["Alice".to_owned()];
        let unknown = vec![];
        let frac =
            SecretService::compute_knowledge_fraction(&known, &unknown, "Alice", SecrecyLevel::Low);
        assert!((frac - 0.8).abs() < f64::EPSILON);
    }

    #[test]
    fn test_compute_knowledge_fraction_unknown() {
        let known = vec!["Bob".to_owned()];
        let unknown = vec!["Alice".to_owned()];
        let frac = SecretService::compute_knowledge_fraction(
            &known,
            &unknown,
            "Alice",
            SecrecyLevel::Medium,
        );
        assert!((frac - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_compute_knowledge_fraction_neutral() {
        let known: Vec<String> = vec![];
        let unknown: Vec<String> = vec![];
        let frac = SecretService::compute_knowledge_fraction(
            &known,
            &unknown,
            "Charlie",
            SecrecyLevel::Medium,
        );
        assert!((frac - 0.1).abs() < f64::EPSILON);
    }

    #[test]
    fn test_compute_knowledge_fraction_public() {
        let known = vec!["Alice".to_owned()];
        let unknown = vec![];
        let frac = SecretService::compute_knowledge_fraction(
            &known,
            &unknown,
            "Alice",
            SecrecyLevel::Public,
        );
        assert!((frac - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_compute_knowledge_fraction_top() {
        let known = vec!["Alice".to_owned()];
        let unknown = vec![];
        let frac =
            SecretService::compute_knowledge_fraction(&known, &unknown, "Alice", SecrecyLevel::Top);
        assert!((frac - 0.15).abs() < f64::EPSILON);
    }

    // ── Service construction test ──

    #[test]
    fn test_secret_service_constructs() {
        let svc = SecretService::new();
        // Just ensure default construction works
        drop(svc);
    }

    #[test]
    fn test_secret_service_default() {
        let _ = SecretService::default();
    }

    // ── SecretDebtSummary serialization ──

    #[test]
    fn test_debt_summary_serialization() {
        let summary = SecretDebtSummary {
            total_debt: 42.0,
            hidden_count: 3,
            partial_count: 2,
            revealed_count: 1,
            details: vec![],
        };
        let json = serde_json::to_string(&summary).unwrap();
        assert!(json.contains("42.0"));
        assert!(json.contains("hidden_count"));
    }

    // ── SecrecyMatrixResult serialization ──

    #[test]
    fn test_secrecy_matrix_result_serialization() {
        let result = SecrecyMatrixResult {
            character_name: "Alice".into(),
            known: vec![SecretMatrixEntry {
                secret_id: "s1".into(),
                description: "test".into(),
                secrecy_level: SecrecyLevel::Low,
                debt: 3.0,
            }],
            unknown: vec![],
            chain_count: 0,
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("Alice"));
        assert!(json.contains("s1"));
    }

    // ── SecretConflict serialization ──

    #[test]
    fn test_secret_conflict_serialization() {
        let conflict = SecretConflict {
            secret_a_id: "a".into(),
            secret_a_description: "desc a".into(),
            secret_b_id: "b".into(),
            secret_b_description: "desc b".into(),
            conflict_reason: "test reason".into(),
            severity: "high".into(),
        };
        let json = serde_json::to_string(&conflict).unwrap();
        assert!(json.contains("high"));
        assert!(json.contains("test reason"));
    }

    // ── PartialReveal serialization ──

    #[test]
    fn test_partial_reveal_serialization() {
        let reveal = PartialReveal {
            secret_id: "s1".into(),
            description: "desc".into(),
            known_by: vec!["Alice".into()],
            unknown_to: vec!["Bob".into()],
            level: SecrecyLevel::Medium,
            character_knows: true,
            knowledge_fraction: 0.5,
        };
        let json = serde_json::to_string(&reveal).unwrap();
        assert!(json.contains("Alice"));
        assert!(json.contains("Bob"));
        assert!(json.contains("medium"));
    }

    // ── SecretChainNode serialization ──

    #[test]
    fn test_secret_chain_node_serialization() {
        let node = SecretChainNode {
            secret_id: "s1".into(),
            description: "秘密A".into(),
            level: SecrecyLevel::High,
            leads_to: vec!["s2".into()],
            discovered_by: vec![],
        };
        let json = serde_json::to_string(&node).unwrap();
        assert!(json.contains("s1"));
        assert!(json.contains("s2"));
        assert!(json.contains("high"));
    }
}
