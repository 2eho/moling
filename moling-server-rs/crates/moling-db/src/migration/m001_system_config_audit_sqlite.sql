-- Migration 001: System config audit trail (SQLite edition)
-- Adds version tracking and immutable audit log to system_config table.

-- Step 1: Add version column (SQLite: no IF NOT EXISTS for ALTER TABLE)
ALTER TABLE system_config ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE system_config ADD COLUMN created_at DATETIME;

-- Backfill created_at for existing rows
UPDATE system_config SET created_at = datetime('now') WHERE created_at IS NULL;

-- Step 2: Create audit log table (append-only, immutable)
CREATE TABLE IF NOT EXISTS system_config_audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key  VARCHAR(128) NOT NULL,
    version     INTEGER NOT NULL,
    old_value   TEXT,
    new_value   TEXT NOT NULL,
    changed_by  VARCHAR(64),
    changed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_config_audit_key_version
    ON system_config_audit (config_key, version DESC);

-- Step 3: Seed default config (idempotent)
INSERT OR IGNORE INTO system_config (key, value, description, version) VALUES
    ('llm_api_base', 'https://api.deepseek.com', 'LLM API 地址', 1);

INSERT OR IGNORE INTO system_config (key, value, description, version) VALUES
    ('llm_api_key', '', 'LLM API 密钥 (加密存储)', 1);

INSERT OR IGNORE INTO system_config (key, value, description, version) VALUES
    ('llm_model', 'deepseek-v4-pro', 'LLM 模型名称', 1);
