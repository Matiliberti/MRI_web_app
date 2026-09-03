# MRI Display — Web App

Upload images and videos from your phone or browser. Each Raspberry Pi polls its own media table and shows the latest file.

## Two independent displays, one deployment

| Display | Web URL (same Vercel project) | Feed table        | Pi kit            |
|--------:|-------------------------------|-------------------|-------------------|
| 1       | `/`                           | `display_media`   | `pi/display-1/`   |
| 2       | `/display-2`                  | `display_media_2` | `pi/display-2/`   |

Display config lives in `lib/displays.ts`; the shared UI is `components/DisplayApp.tsx`.
Each Pi is told which display it is by `DISPLAY_ID` in its `.env` — see `pi/README.md`.
To add a display 3: add an entry in `lib/displays.ts`, a route folder `app/display-3/`,
a SQL file like `supabase/002_add_display_2.sql`, and a `pi/display-3/` folder.

---

## 1. Supabase Setup

### Database tables

SQL lives in `supabase/`. Run in **Supabase Dashboard → SQL Editor → New query**:

- `001_schema_display_1.sql` — the original schema (already applied in production; reference only / rebuild from scratch).
- `002_add_display_2.sql` — additive migration that adds display 2. Safe to run on the live project.

### Storage bucket

1. Go to **Storage** in the Supabase dashboard.
2. Click **New bucket**, name it exactly `media`, and tick **Public bucket**.
3. The default RLS policy on a public bucket already allows uploads — no extra SQL needed.

---

## 2. Environment variables

Copy `.env.local.example` to `.env.local` and fill in your values:

```bash
cp .env.local.example .env.local
```

Find the values in **Supabase → Project Settings → API**:
- `NEXT_PUBLIC_SUPABASE_URL` → Project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` → `anon` / `public` key
- Project URL: https://waofjhvilkuftwesfefm.supabase.co/rest/v1/
- Anon_key: sb_publishable_x9VBkmIuJVr7VbB8ScOW_g_eIXwJGEl

---

## 3. Run locally

```bash
npm install
npm run dev
# Open http://localhost:3000
```

---

## 4. Deploy to Vercel

```bash
# One-time
npm i -g vercel
vercel

# Follow the prompts, then add env vars in the Vercel dashboard:
# Settings → Environment Variables → add the two NEXT_PUBLIC_* vars
```

Or connect the repo in the Vercel web UI — it auto-detects Next.js and deploys on every push.

---

## How it works

| Step | What happens |
|------|--------------|
| User taps upload | File is sent to the `media` Supabase Storage bucket |
| Public URL retrieved | `getPublicUrl()` returns a permanent CDN link |
| Row inserted | `display_media` gets `{ file_url, created_at }` |
| Pi polls the table | Pi fetches the latest row and displays that URL |

The Pi-side daemon is in `pi/common/display_media.py`; per-display install kits are in `pi/display-1/` and `pi/display-2/` (see `pi/README.md`).
