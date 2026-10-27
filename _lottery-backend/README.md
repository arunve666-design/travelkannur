# Coupon Number Draw — backend

- **Live page:** https://travelkannur.in/lottery/ (`lottery/index.html`)
- **Demo (no backend, runs in the browser):** https://travelkannur.in/lottery/demo.html

Both pages are hidden from search engines (`noindex` + `robots.txt`), not in the sitemap and not linked from the site.

## How the draw works

1. The page lists tiles **100–1300**.
2. A customer taps a tile, enters name + phone (and a coupon code if enabled) and taps **Open tile**.
3. The tile shuffles and reveals a **random hidden number (100–1300) that nobody has received yet**.
4. From then on the **tile is gone for everyone** and the **number can never come out of another tile**.
   The tile list refreshes every 15 seconds; if two people tap the same tile at once, the server gives it
   to the first and asks the second to choose another.
5. Each phone number gets one pick. Trying again shows the original result.

## One-time setup (on a computer)

1. Create a new Google Sheet → **Extensions → Apps Script**.
2. Replace `Code.gs` with `Code.gs` from this folder. Save.
3. Reload the Sheet → **Lottery → Set up / reset**, allow permissions. Tiles and numbers 100–1300 are created.
4. **Deploy → New deployment → Web app**, Execute as **Me**, Who has access **Anyone** → Deploy. Copy the URL (ends in `/exec`).
5. In `lottery/index.html`, paste that URL into `var API_URL = "";` and commit. The page goes live within a minute or two.

After changing `Code.gs`, use **Deploy → Manage deployments → Edit → New version** so the URL stays the same.

## Running the draw (all in the Sheet)

| Tab | What it holds |
|---|---|
| **Draws** | Official results: draw #, tile picked, number revealed, name, phone, coupon code, time |
| **Log** | Every page visit, pick, repeat attempt, taken-tile clash, rejection and error, hash-chained so later edits are detectable |
| **Pool** | Every value 100–1300: is the tile used, is the number given, and in which draw |
| **Settings** | `open` (TRUE/FALSE), range, `require_code` |
| **Codes** | Optional one-time coupon codes |

**Lottery menu:** Run integrity check · Open / Close the draw · Generate coupon codes · Set up / reset.

The integrity check confirms every tile was picked once, every number was given out once, every phone
picked once, the Pool matches the Draws list, and the log hash chain is unbroken.
