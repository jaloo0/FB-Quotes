# FB-Quotes — Automated Facebook Quote Machine

## Architecture

```
main.py                   ← Orchestrator
pipeline/
  vibe_engine.py          ← Mood roll + quote library
  image_fetcher.py        ← Pexels API + tag analysis
  ai_quote_finisher.py    ← Gemini Flash AI + local fallback
  style_engine.py         ← Three visual styles (A/B/C)
  fb_poster.py            ← Facebook Graph API
  assets/
    Outfit-Bold.ttf       ← Font (place here manually)
.github/workflows/
  auto_post.yml           ← Runs every 12 hours
requirements.txt
```

---

## 4 Vibes

| Vibe | Mood | Sample Pexels Query |
|------|------|---------------------|
| Defeat | Quiet loss, introspection | `gloomy abandoned street` |
| Resilience | Rising back, raw strength | `hero silhouette sunrise` |
| Peak | Luxury, quiet success | `dark cinematic luxury car` |
| Mystery | Layers, unknown depth | `cinematic dark figure mist` |

---

## 3 Visual Styles

| Style | Name | Technique |
|-------|------|-----------|
| A | Inverted Cursor | XOR-inverts text pixels vs background → always-legible |
| B | Subject Sandwich | `rembg` isolates hero → text lives *behind* subject |
| C | Frosted Depth | Gaussian blur BG + sharp centre + frosted glass text bar |

---

## Setup — GitHub Secrets Required

Go to **Repo → Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Where to get it |
|-------------|-----------------|
| `PEXELS_API_KEY` | [pexels.com/api](https://www.pexels.com/api/) — Free |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) — Free |
| `FB_PAGE_ID` | Facebook Page → About → Page ID |
| `FB_PAGE_ACCESS_TOKEN` | [developers.facebook.com](https://developers.facebook.com/) → Graph API Explorer → long-lived page token |

---

## Font

Download **Outfit Bold** (free, Google Fonts) and place it at:

```
pipeline/assets/Outfit-Bold.ttf
```

[Download link →](https://fonts.google.com/specimen/Outfit)

---

## Local Test Run

```bash
pip install -r requirements.txt

# Set env vars (PowerShell)
$env:PEXELS_API_KEY       = "your_key"
$env:GEMINI_API_KEY       = "your_key"
$env:FB_PAGE_ID           = "your_page_id"
$env:FB_PAGE_ACCESS_TOKEN = "your_token"

python main.py
```

The pipeline will:
1. Roll a vibe
2. Fetch + filter a Pexels image
3. Generate / AI-finish a quote
4. Apply a random visual style → save to `tmp_assets/`
5. Post to your Facebook Page
6. Delete `tmp_assets/`

---

## Schedule

The GitHub Action fires at **00:00 UTC** and **12:00 UTC** daily (2 posts/day).
You can also trigger it manually from the **Actions** tab → **Run workflow**.

---

## Cost

| Service | Cost |
|---------|------|
| GitHub Actions | Free (2 000 min/month on free plan; each run ≈ 2 min) |
| Pexels API | Free |
| Gemini 1.5 Flash | Free tier (1 M tokens/day) |
| Facebook Graph API | Free |
| **Total** | **$0** |
