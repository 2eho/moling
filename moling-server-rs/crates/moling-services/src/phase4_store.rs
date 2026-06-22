//! Phase4Store — dual-mode Redis / in-memory backend for Phase4 coordination.
//!
//! Provides a unified interface for:
//! - Nonce deduplication (Set operations)
//! - Distributed locking (SET NX EX / RwLock-based)
//! - Task state persistence (String set/get)
//!
//! When a Redis connection is available the store uses it for durability and
//! cross-worker coordination; when Redis is absent it falls back to in-memory
//! data structures (suitable for single-worker development).
//!
//! Mirrors Python `app/service/phase4_store.py`.

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;

// ---------------------------------------------------------------------------
// In-memory backend
// ---------------------------------------------------------------------------

/// Thread-safe in-memory store implementing the same interface as Redis.
struct MemoryBackend {
    nonces: RwLock<Vec<Vec<String>>>,
    nonce_cache: RwLock<HashMap<String, bool>>,
    locks: RwLock<HashMap<String, String>>,
    tasks: RwLock<HashMap<String, String>>,
}

impl MemoryBackend {
    fn new() -> Self {
        Self {
            nonces: RwLock::new(Vec::new()),
            nonce_cache: RwLock::new(HashMap::new()),
            locks: RwLock::new(HashMap::new()),
            tasks: RwLock::new(HashMap::new()),
        }
    }

    async fn sismember(&self, _key: &str, member: &str) -> bool {
        let cache = self.nonce_cache.read().await;
        if let Some(&present) = cache.get(member) {
            return present;
        }
        drop(cache);

        let nonces = self.nonces.read().await;
        let present = nonces.iter().any(|ns| ns.iter().any(|n| n == member));
        drop(nonces);

        let mut cache = self.nonce_cache.write().await;
        cache.insert(member.to_string(), present);
        if cache.len() > 1000 {
            let oldest = cache.keys().next().cloned();
            if let Some(k) = oldest {
                cache.remove(&k);
            }
        }
        present
    }

    async fn sadd(&self, _key: &str, member: &str) -> bool {
        let mut nonces = self.nonces.write().await;
        for ns in nonces.iter() {
            if ns.iter().any(|n| n == member) {
                return false;
            }
        }
        if nonces.is_empty() {
            nonces.push(Vec::new());
        }
        nonces[0].push(member.to_string());
        while nonces[0].len() > 5000 {
            nonces[0].remove(0);
        }
        // Update cache so subsequent check_nonce sees the new entry
        let mut cache = self.nonce_cache.write().await;
        cache.insert(member.to_string(), true);
        drop(nonces);
        true
    }

    async fn setnx_ex(&self, lock_key: &str, owner_id: &str, _ttl: u64) -> bool {
        let mut locks = self.locks.write().await;
        if locks.contains_key(lock_key) {
            return false;
        }
        locks.insert(lock_key.to_string(), owner_id.to_string());
        true
    }

    async fn get_lock_owner(&self, lock_key: &str) -> Option<String> {
        let locks = self.locks.read().await;
        locks.get(lock_key).cloned()
    }

    async fn release_lock(&self, lock_key: &str, owner_id: &str) -> bool {
        let mut locks = self.locks.write().await;
        match locks.get(lock_key) {
            Some(current) if current == owner_id => {
                locks.remove(lock_key);
                true
            }
            None => true,
            _ => false,
        }
    }

    async fn hset_task(&self, task_id: &str, data: &str) {
        let mut tasks = self.tasks.write().await;
        tasks.insert(task_id.to_string(), data.to_string());
    }

    async fn hget_task(&self, task_id: &str) -> Option<String> {
        let tasks = self.tasks.read().await;
        tasks.get(task_id).cloned()
    }
}

// ---------------------------------------------------------------------------
// Redis backend
// ---------------------------------------------------------------------------

/// Redis-backed store using `RedisClient` from moling-core.
struct RedisBackend {
    client: RedisClient,
}

impl RedisBackend {
    const NONCE_KEY: &'static str = "phase4:nonces";

    fn new(client: RedisClient) -> Self {
        Self { client }
    }

    async fn sismember(&self, _key: &str, member: &str) -> AppResult<bool> {
        match self.client.sismember(Self::NONCE_KEY, member).await? {
            Some(v) => Ok(v),
            None => Ok(false),
        }
    }

    async fn sadd(&self, _key: &str, member: &str) -> AppResult<bool> {
        let before = self.sismember(_key, member).await?;
        if before {
            return Ok(false);
        }
        match self.client.sadd(Self::NONCE_KEY, member).await? {
            Some(_) => Ok(true),
            None => Ok(false),
        }
    }

    async fn setnx_ex(&self, lock_key: &str, owner_id: &str, ttl: u64) -> AppResult<bool> {
        // Use SET with NX: if key exists, return existing value; if not, set it.
        let existing = self.client.get(lock_key).await?;
        if existing.is_some() {
            return Ok(false);
        }
        match self.client.setex(lock_key, owner_id, ttl).await? {
            Some(_) => Ok(true),
            None => Ok(false),
        }
    }

    async fn get_lock_owner(&self, lock_key: &str) -> AppResult<Option<String>> {
        self.client.get(lock_key).await
    }

    async fn release_lock(&self, lock_key: &str, owner_id: &str) -> AppResult<bool> {
        let current = self.client.get(lock_key).await?;
        match current {
            None => Ok(true),
            Some(ref val) if val == owner_id => {
                self.client.del(lock_key).await?;
                Ok(true)
            }
            _ => Ok(false),
        }
    }

    async fn hset_task(&self, task_id: &str, data: &str) -> AppResult<()> {
        let key = format!("phase4:task:{}", task_id);
        self.client.setex(&key, data, 3600).await?;
        Ok(())
    }

    async fn hget_task(&self, task_id: &str) -> AppResult<Option<String>> {
        let key = format!("phase4:task:{}", task_id);
        self.client.get(&key).await
    }
}

// ---------------------------------------------------------------------------
// Backend enum
// ---------------------------------------------------------------------------

enum Backend {
    Memory(MemoryBackend),
    Redis(RedisBackend),
}

// ---------------------------------------------------------------------------
// Phase4Store — unified interface
// ---------------------------------------------------------------------------

/// Dual-mode store: Redis if available, otherwise in-memory.
#[derive(Clone)]
pub struct Phase4Store {
    backend: Arc<Backend>,
    use_redis: bool,
}

impl Phase4Store {
    /// Create a new store, defaulting to memory mode.
    pub fn new() -> Self {
        Self {
            backend: Arc::new(Backend::Memory(MemoryBackend::new())),
            use_redis: false,
        }
    }

    /// Initialize the store. Pass `Some(client)` for Redis mode or `None` for memory mode.
    pub async fn init(&mut self, redis_client: Option<RedisClient>) -> AppResult<()> {
        if let Some(client) = redis_client {
            match client.ping().await? {
                Some(ref pong) if pong == "PONG" => {
                    self.backend = Arc::new(Backend::Redis(RedisBackend::new(client)));
                    self.use_redis = true;
                    tracing::info!("Phase4Store: using Redis backend");
                }
                _ => {
                    tracing::warn!("Phase4Store: Redis ping failed, using memory backend");
                }
            }
        } else {
            tracing::info!("Phase4Store: Redis not available, using memory backend");
        }
        Ok(())
    }

    /// Returns the backend type string ("redis" or "memory").
    pub fn backend_type(&self) -> &str {
        if self.use_redis { "redis" } else { "memory" }
    }

    // -- nonce -------------------------------------------------------------

    pub async fn check_nonce(&self, nonce: &str) -> AppResult<bool> {
        match &*self.backend {
            Backend::Memory(m) => Ok(m.sismember("nonces", nonce).await),
            Backend::Redis(r) => r.sismember("nonces", nonce).await,
        }
    }

    pub async fn record_nonce(&self, nonce: &str) -> AppResult<bool> {
        match &*self.backend {
            Backend::Memory(m) => Ok(m.sadd("nonces", nonce).await),
            Backend::Redis(r) => r.sadd("nonces", nonce).await,
        }
    }

    // -- lock --------------------------------------------------------------

    pub async fn acquire_lock(&self, resource: &str, owner_id: &str, ttl_secs: u64) -> AppResult<bool> {
        let lock_key = format!("phase4:lock:{}", resource);
        match &*self.backend {
            Backend::Memory(m) => Ok(m.setnx_ex(&lock_key, owner_id, ttl_secs).await),
            Backend::Redis(r) => r.setnx_ex(&lock_key, owner_id, ttl_secs).await,
        }
    }

    pub async fn get_lock_owner(&self, resource: &str) -> AppResult<Option<String>> {
        let lock_key = format!("phase4:lock:{}", resource);
        match &*self.backend {
            Backend::Memory(m) => Ok(m.get_lock_owner(&lock_key).await),
            Backend::Redis(r) => r.get_lock_owner(&lock_key).await,
        }
    }

    pub async fn release_lock(&self, resource: &str, owner_id: &str) -> AppResult<bool> {
        let lock_key = format!("phase4:lock:{}", resource);
        match &*self.backend {
            Backend::Memory(m) => Ok(m.release_lock(&lock_key, owner_id).await),
            Backend::Redis(r) => r.release_lock(&lock_key, owner_id).await,
        }
    }

    // -- task --------------------------------------------------------------

    pub async fn save_task(&self, task_id: &str, data: &str) -> AppResult<()> {
        match &*self.backend {
            Backend::Memory(m) => { m.hset_task(task_id, data).await; Ok(()) }
            Backend::Redis(r) => r.hset_task(task_id, data).await,
        }
    }

    pub async fn get_task(&self, task_id: &str) -> AppResult<Option<String>> {
        match &*self.backend {
            Backend::Memory(m) => Ok(m.hget_task(task_id).await),
            Backend::Redis(r) => r.hget_task(task_id).await,
        }
    }
}

impl Default for Phase4Store {
    fn default() -> Self { Self::new() }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_memory_store_nonce() {
        let store = Phase4Store::new();
        assert!(!store.check_nonce("task-1").await.unwrap());
        assert!(store.record_nonce("task-1").await.unwrap());
        assert!(store.check_nonce("task-1").await.unwrap());
        assert!(!store.record_nonce("task-1").await.unwrap());
    }

    #[tokio::test]
    async fn test_memory_store_lock() {
        let store = Phase4Store::new();
        assert!(store.acquire_lock("project:1", "worker-a", 30).await.unwrap());
        assert!(!store.acquire_lock("project:1", "worker-b", 30).await.unwrap());
        assert!(store.release_lock("project:1", "worker-a").await.unwrap());
        assert!(store.acquire_lock("project:1", "worker-b", 30).await.unwrap());
    }

    #[tokio::test]
    async fn test_memory_store_task() {
        let store = Phase4Store::new();
        store.save_task("t1", r#"{"status":"running"}"#).await.unwrap();
        let data = store.get_task("t1").await.unwrap();
        assert_eq!(data, Some(r#"{"status":"running"}"#.to_string()));
        assert!(store.get_task("nonexistent").await.unwrap().is_none());
    }

    #[tokio::test]
    async fn test_memory_store_lock_owner_verification() {
        let store = Phase4Store::new();
        store.acquire_lock("res:x", "alice", 30).await.unwrap();
        assert!(!store.release_lock("res:x", "bob").await.unwrap());
        assert!(store.release_lock("res:x", "alice").await.unwrap());
    }
}
