# Coupon Number Draw — backend

The customer page lives at `lottery/index.html` and is served at **https://travelkannur.in/lottery/**.
It is hidden from search engines (`noindex` + `robots.txt`), not in the sitemap and not linked from the site.

The draw itself runs on **Google Apps Script + a Google Sheet** (this folder). The underscore in the
folder name keeps these files off the public website.

## One-time setup (on a computer)

1. Create a new Google Sheet → **Extensions → Apps Script**.
2. Replace `Code.gs` with `Code.gs` from this folder.
3. **+ → HTML**, name it `Index`, paste `Index.html` from this folder (a fallback page served by Apps Script itself).
4. Save, reload the Sheet → **Lottery → Set up / reset**, allow permissions. The pool fills with 100–1300.
5. **Deploy → New deployment → Web app**, Execute as **Me**, Who has access **Anyone** → Deploy. Copy the URL (ends in `/exec`).
6. In `lottery/index.html`, paste that URL into `var API_URL = "";` and commit. The page goes live within a minute or two.

After changing `Code.gs`, use **Deploy → Manage deployments → Edit → New version** so the URL stays the same.

## Running the draw (all in the Sheet)

| Tab | What it holds |
|---|---|
| **Draws** | Official results: draw #, number, name, phone, coupon code, time |
| **Log** | Every page visit, draw, repeat attempt, rejection and error, hash-chained so later edits are detectable |
| **Pool** | Every number and whether it's still available |
| **Settings** | `open` (TRUE/FALSE), number range, `require_code` |
| **Codes** | Optional one-time coupon codes |

**Lottery menu:** Run integrity check · Open / Close the draw · Generate coupon codes · Set up / reset.

## Rules the backend enforces

- Each number is given out once (a server lock serialises draws).
- Each phone number gets one number; trying again returns the original.
- With `require_code` = TRUE, each one-time coupon code works once.
