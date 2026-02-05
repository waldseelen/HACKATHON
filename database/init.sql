-- ============================================================
-- LogSense AI - Database Schema
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- LOGS TABLE: Raw + normalized log storage
-- ============================================================
CREATE TABLE IF NOT EXISTS logs (
    id              BIGSERIAL       PRIMARY KEY,
    ingested_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    container_name  TEXT            NOT NULL,
    service_name    TEXT            NOT NULL,
    severity        TEXT            NOT NULL CHECK (severity IN ('error','warn','fatal','critical','unknown')),
    raw_log         TEXT            NOT NULL,
    normalized      JSONB,
    fingerprint     TEXT
);

CREATE INDEX idx_logs_service_severity  ON logs (service_name, severity);
CREATE INDEX idx_logs_ingested_at       ON logs (ingested_at DESC);
CREATE INDEX idx_logs_fingerprint       ON logs (fingerprint) WHERE fingerprint IS NOT NULL;

-- ============================================================
-- ALERTS TABLE: AI analysis results
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    log_ids             BIGINT[]        NOT NULL,
    -- AI Analysis fields
    category            TEXT            NOT NULL,
    severity            TEXT            NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    summary             TEXT            NOT NULL DEFAULT '',
    root_cause          TEXT            NOT NULL DEFAULT '',
    solution            TEXT            NOT NULL DEFAULT '',
    action_required     BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Notification tracking
    notified_at         TIMESTAMPTZ,
    notification_count  INTEGER         DEFAULT 0,
    -- Extra
    metadata            JSONB           DEFAULT '{}'
);

CREATE INDEX idx_alerts_created_at          ON alerts (created_at DESC);
CREATE INDEX idx_alerts_category_severity   ON alerts (category, severity);

-- ============================================================
-- USER FCM TOKENS: Push notification targets
-- ============================================================
CREATE TABLE IF NOT EXISTS user_fcm_tokens (
    device_token        TEXT        PRIMARY KEY,
    user_id             TEXT,
    display_name        TEXT,
    service_filters     TEXT[]      DEFAULT ARRAY[]::TEXT[],
    severity_threshold  TEXT        DEFAULT 'high',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SERVICE METRICS: For Grafana dashboards
-- ============================================================
CREATE TABLE IF NOT EXISTS service_metrics (
    id              BIGSERIAL       PRIMARY KEY,
    recorded_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    metric_name     TEXT            NOT NULL,
    service_name    TEXT,
    value           DOUBLE PRECISION NOT NULL,
    labels          JSONB           DEFAULT '{}'
);

CREATE INDEX idx_metrics_recorded_at    ON service_metrics (recorded_at DESC);
CREATE INDEX idx_metrics_name           ON service_metrics (metric_name, recorded_at DESC);

-- ============================================================
-- SEED DATA: Test FCM token
-- ============================================================
INSERT INTO user_fcm_tokens (device_token, user_id, display_name, service_filters, severity_threshold)
VALUES
    ('test-device-token-1', 'dev-user-1', 'Developer', ARRAY['nginx','postgres','api-gateway'], 'high'),
    ('test-device-token-2', 'dev-user-2', 'SRE Lead',  ARRAY['*'], 'critical')
ON CONFLICT (device_token) DO NOTHING;
