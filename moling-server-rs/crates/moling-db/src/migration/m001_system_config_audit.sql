-- Migration 001: System config audit trail
-- Adds version tracking and immutable audit log to system_config table.

-- Step 1: Add version column (optimistic lock)
ALTER TABLE system_config ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- Step 2: Create audit log table (append-only, immutable)
CREATE TABLE IF NOT EXISTS system_config_audit (
    id          BIGSERIAL PRIMARY KEY,
    config_key  VARCHAR(128) NOT NULL,
    version     INTEGER NOT NULL,
    old_value   TEXT,
    new_value   TEXT NOT NULL,
    changed_by  VARCHAR(64),
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_config_audit_key_version
    ON system_config_audit (config_key, version DESC);

-- Step 3: Create audit trigger function
CREATE OR REPLACE FUNCTION fn_system_config_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO system_config_audit (config_key, version, old_value, new_value, changed_by)
    VALUES (
        NEW.key,
        NEW.version,
        OLD.value,
        NEW.value,
        current_setting('moling.operator', true)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Attach trigger (drop first to make re-runnable)
DROP TRIGGER IF EXISTS trg_system_config_audit ON system_config;
CREATE TRIGGER trg_system_config_audit
    AFTER UPDATE ON system_config
    FOR EACH ROW
    WHEN (OLD.value IS DISTINCT FROM NEW.value)
    EXECUTE FUNCTION fn_system_config_audit();

-- Step 5: Seed default config (idempotent)
INSERT INTO system_config (key, value, description, version)
VALUES
    ('llm_api_base', 'https://api.deepseek.com',     'LLM API 地址', 1),
    ('llm_api_key',  '',                              'LLM API 密钥 (加密存储)', 1),
    ('llm_model',    'deepseek-v4-pro',               'LLM 模型名称', 1)
ON CONFLICT (key) DO NOTHING;
