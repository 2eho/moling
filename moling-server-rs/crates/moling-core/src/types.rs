use chrono::{DateTime, Utc};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::fmt;
use std::str::FromStr;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// MolingId — UUID v4 wrapper
// ---------------------------------------------------------------------------

/// Strongly-typed UUID v4 identifier for all Moling entities.
///
/// Wraps a [`uuid::Uuid`] and guarantees the v4 variant through its
/// constructors.  Serializes as a standard hyphenated UUID string.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct MolingId(Uuid);

impl MolingId {
    /// Create a new random UUID v4 identifier.
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }

    /// Parse a [`MolingId`] from a hyphenated UUID string.
    ///
    /// Returns an error if the string does not represent a valid UUID.
    pub fn parse(s: &str) -> Result<Self, uuid::Error> {
        Uuid::parse_str(s).map(Self)
    }

    /// Return a reference to the inner [`Uuid`].
    pub fn as_uuid(&self) -> &Uuid {
        &self.0
    }
}

impl Default for MolingId {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for MolingId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl FromStr for MolingId {
    type Err = uuid::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Self::parse(s)
    }
}

impl Serialize for MolingId {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        self.0.serialize(serializer)
    }
}

impl<'de> Deserialize<'de> for MolingId {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        Uuid::deserialize(deserializer).map(Self)
    }
}

// ---------------------------------------------------------------------------
// MolingDateTime — UTC datetime wrapper
// ---------------------------------------------------------------------------

/// Timezone-aware UTC datetime wrapper.
///
/// Newtype over [`chrono::DateTime<Utc>`] with ISO-8601 / RFC-3339
/// string serialization.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct MolingDateTime(DateTime<Utc>);

impl MolingDateTime {
    /// Return the current instant in UTC.
    pub fn now() -> Self {
        Self(Utc::now())
    }

    /// Parse an RFC 3339 / ISO 8601 string into a [`MolingDateTime`].
    pub fn parse_rfc3339(s: &str) -> Result<Self, chrono::ParseError> {
        DateTime::parse_from_rfc3339(s).map(|dt| Self(dt.with_timezone(&Utc)))
    }

    /// Return a reference to the inner [`DateTime<Utc>`].
    pub fn as_datetime(&self) -> &DateTime<Utc> {
        &self.0
    }
}

impl fmt::Display for MolingDateTime {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0.to_rfc3339())
    }
}

impl Serialize for MolingDateTime {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&self.0.to_rfc3339())
    }
}

impl<'de> Deserialize<'de> for MolingDateTime {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let s = String::deserialize(deserializer)?;
        DateTime::parse_from_rfc3339(&s)
            .map(|dt| Self(dt.with_timezone(&Utc)))
            .map_err(serde::de::Error::custom)
    }
}

// ---------------------------------------------------------------------------
// Traits
// ---------------------------------------------------------------------------

/// Entities that carry `created_at` / `updated_at` timestamps.
///
/// Mirrors Python `TimestampMixin`.
pub trait Timestamped {
    /// When the entity was first persisted.
    fn created_at(&self) -> MolingDateTime;

    /// When the entity was last modified.
    fn updated_at(&self) -> MolingDateTime;
}

/// Entities that support soft-delete.
///
/// Mirrors Python `SoftDeleteMixin`.
pub trait SoftDeletable {
    /// The point in time the entity was soft-deleted, or `None` if still
    /// active.
    fn deleted_at(&self) -> Option<MolingDateTime>;

    /// Convenience helper: returns `true` when the entity has been
    /// soft-deleted.
    fn is_deleted(&self) -> bool {
        self.deleted_at().is_some()
    }
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

/// Input pagination parameters.
///
/// Mirrors Python `PaginationReq` schema.
#[derive(Debug, Clone, Deserialize)]
pub struct Pagination {
    /// 1-based page number (defaults to 1).
    #[serde(default = "default_page")]
    pub page: u32,

    /// Number of items per page (defaults to 20, capped at 500).
    #[serde(default = "default_page_size")]
    pub page_size: u32,
}

fn default_page() -> u32 {
    1
}

fn default_page_size() -> u32 {
    20
}

/// Generic paginated response.
///
/// Mirrors Python `PaginatedResp`.
#[derive(Debug, Serialize)]
pub struct PaginatedResult<T: Serialize> {
    pub items: Vec<T>,
    pub total: u64,
    pub page: u32,
    pub page_size: u32,
    pub total_pages: u32,
}

impl Pagination {
    /// Zero-based offset suitable for SQL `OFFSET` / `LIMIT` clauses.
    pub fn offset(&self) -> u64 {
        (self.page.saturating_sub(1) as u64) * self.limit()
    }

    /// Effective page size, capped at 500.
    pub fn limit(&self) -> u64 {
        std::cmp::min(self.page_size, 500) as u64
    }
}

impl<T: Serialize> PaginatedResult<T> {
    /// Construct a [`PaginatedResult`] from raw items, total count, and the
    /// input [`Pagination`] parameters.
    pub fn new(items: Vec<T>, total: u64, pagination: &Pagination) -> Self {
        let effective_page_size = pagination.limit() as u32;
        let total_pages = if effective_page_size == 0 {
            0
        } else {
            total.div_ceil(effective_page_size as u64) as u32
        };
        Self {
            items,
            total,
            page: pagination.page,
            page_size: effective_page_size,
            total_pages,
        }
    }
}
