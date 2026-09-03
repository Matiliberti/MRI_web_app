-- =============================================================================
-- Add display 2  (safe to run on the LIVE project)
-- -----------------------------------------------------------------------------
-- Purely additive: creates a new feed table and adds id=2 rows. Nothing that
-- display 1 (web route "/" and Pi 1) reads or writes is touched.
-- Run in Supabase Dashboard -> SQL Editor -> New query.
-- =============================================================================

CREATE TABLE IF NOT EXISTS display_media_2 (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  file_url         TEXT        NOT NULL,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  cache_locally    BOOLEAN     NOT NULL DEFAULT TRUE,
  pi_downloaded_at TIMESTAMPTZ
);

ALTER TABLE display_media_2 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public_all" ON display_media_2;
CREATE POLICY "public_all" ON display_media_2 FOR ALL USING (true) WITH CHECK (true);

-- Heartbeat + volume rows for display 2 (Pi 2 upserts/reads id = 2).
INSERT INTO pi_status   (id) VALUES (2) ON CONFLICT (id) DO NOTHING;
INSERT INTO pi_settings (id) VALUES (2) ON CONFLICT (id) DO NOTHING;

-- Verify:
--   SELECT * FROM pi_status;      -- rows 1 and 2
--   SELECT * FROM pi_settings;    -- rows 1 and 2
--   SELECT count(*) FROM display_media_2;   -- 0
