-- =============================================================================
-- Display 1 schema (reference / rebuild only)
-- -----------------------------------------------------------------------------
-- This is what the ORIGINAL single-display deployment uses and what the code
-- expects. It already exists in the production Supabase project; do NOT re-run
-- it there. Use it only to rebuild the project from scratch.
-- =============================================================================

-- Feed for display 1. The Pi plays the newest row.
CREATE TABLE IF NOT EXISTS display_media (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  file_url         TEXT        NOT NULL,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  cache_locally    BOOLEAN     NOT NULL DEFAULT TRUE,
  pi_downloaded_at TIMESTAMPTZ
);

-- Heartbeat: one row per display, keyed by display id.
CREATE TABLE IF NOT EXISTS pi_status (
  id        INTEGER     PRIMARY KEY,
  last_seen TIMESTAMPTZ
);

-- Settings: one row per display, keyed by display id.
-- volume is a raw PipeWire gain (0.0 .. 2.0).
CREATE TABLE IF NOT EXISTS pi_settings (
  id     INTEGER          PRIMARY KEY,
  volume DOUBLE PRECISION NOT NULL DEFAULT 1.0
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
DROP POLICY IF EXISTS "public_all" ON pi_settings;
CREATE POLICY "public_all" ON pi_settings   FOR ALL USING (true) WITH CHECK (true);

-- Storage: a PUBLIC bucket named "media" (create it in Dashboard -> Storage).
-- Shared by all displays; file names are unique per upload.
