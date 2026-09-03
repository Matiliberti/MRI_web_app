-- =============================================================================
-- Display 1 schema (reference / rebuild only)
-- -----------------------------------------------------------------------------
-- This is what the ORIGINAL single-display deployment uses and what the code
-- expects. It already exists in the production Supabase project; do NOT re-run
-- it there. Use it only to rebuild the project from scratch.
-- =============================================================================

-- Feed for display 1. The Pi plays the newest row.
-- NOTE (verified 2026-09-03): production has NO pi_downloaded_at column, so
-- the "received by Pi" badge never shows for display 1 and the daemon's
-- download-ack update fails silently. The web app tolerates its absence.
-- To enable it (additive, safe):
--   ALTER TABLE display_media ADD COLUMN IF NOT EXISTS pi_downloaded_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS display_media (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  file_url      TEXT        NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  cache_locally BOOLEAN     NOT NULL DEFAULT TRUE
);

-- Heartbeat: one row per display, keyed by display id.
-- (Originally created with CHECK (id = 1) named "single_row"; 002 relaxes it.)
CREATE TABLE IF NOT EXISTS pi_status (
  id        INTEGER     PRIMARY KEY DEFAULT 1,
  last_seen TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT one_row_per_display CHECK (id >= 1)
);

-- Settings: one row per display, keyed by display id.
-- volume is a raw PipeWire gain (0.0 .. 2.0).
CREATE TABLE IF NOT EXISTS pi_settings (
  id     INTEGER PRIMARY KEY DEFAULT 1,
  volume REAL    DEFAULT 1.0
);

INSERT INTO pi_status   (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
INSERT INTO pi_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Public read/write for the anon key (private tool, no auth).
ALTER TABLE display_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE pi_status     ENABLE ROW LEVEL SECURITY;
ALTER TABLE pi_settings   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_all" ON display_media;
CREATE POLICY "public_all" ON display_media FOR ALL USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "public_all" ON pi_status;
CREATE POLICY "public_all" ON pi_status     FOR ALL USING (true) WITH CHECK (true);
-- pi_settings is deliberately read+update only (no insert/delete from anon);
-- rows are created by migrations.
DROP POLICY IF EXISTS "read pi_settings"   ON pi_settings;
CREATE POLICY "read pi_settings"   ON pi_settings FOR SELECT USING (true);
DROP POLICY IF EXISTS "update pi_settings" ON pi_settings;
CREATE POLICY "update pi_settings" ON pi_settings FOR UPDATE USING (true) WITH CHECK (true);

-- Storage: a PUBLIC bucket named "media" (create it in Dashboard -> Storage).
-- Shared by all displays; file names are unique per upload.
