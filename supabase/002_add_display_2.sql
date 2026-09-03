-- =============================================================================
-- Add display 2  (safe to run on the LIVE project)
-- -----------------------------------------------------------------------------
-- Additive: creates a new feed table and adds id=2 rows. The only change to an
-- existing object is relaxing pi_status's CHECK (id = 1) so it allows one row
-- per display; Pi 1 keeps writing id = 1 exactly as before.
-- Run in Supabase Dashboard -> SQL Editor -> New query.
-- =============================================================================

-- Same columns as display_media plus pi_downloaded_at, which the code already
-- supports (drives the "received by Pi" badge; display 1 lacks the column).
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

-- pi_status was created with CHECK (id = 1) ("single_row"). Allow one row per
-- display instead. Metadata-only; existing row 1 is unaffected.
ALTER TABLE pi_status DROP CONSTRAINT IF EXISTS single_row;
ALTER TABLE pi_status DROP CONSTRAINT IF EXISTS one_row_per_display;
ALTER TABLE pi_status ADD CONSTRAINT one_row_per_display CHECK (id >= 1);

-- Heartbeat + volume rows for display 2 (Pi 2 upserts/reads id = 2).
INSERT INTO pi_status   (id) VALUES (2) ON CONFLICT (id) DO NOTHING;
INSERT INTO pi_settings (id) VALUES (2) ON CONFLICT (id) DO NOTHING;

-- Verify:
--   SELECT * FROM pi_status;      -- rows 1 and 2
--   SELECT * FROM pi_settings;    -- rows 1 and 2
--   SELECT count(*) FROM display_media_2;   -- 0
