# MRI Display — Web App

Upload images and videos from your phone or browser. The Raspberry Pi polls the `display_media` table and shows the latest file.

---

## 1. Supabase Setup

### Database table

Run this in the **Supabase SQL Editor** (Dashboard → SQL Editor → New query):

```sql
-- Table
CREATE TABLE display_media (
  id         UUID                     DEFAULT gen_random_uuid() PRIMARY KEY,
  file_url   TEXT                     NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Allow public read/write (no auth needed for a private 2-person tool)
ALTER TABLE display_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_all" ON display_media
  FOR ALL USING (true) WITH CHECK (true);
```

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

The Pi-side script is separate — it just needs to `SELECT file_url FROM display_media ORDER BY created_at DESC LIMIT 1` on a polling loop.
