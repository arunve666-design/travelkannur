# Coupon Number Draw — backend

- **Live page:** https://travelkannur.in/lottery/ (`lottery/index.html`)
- **Demo (no backend, runs in the browser):** https://travelkannur.in/lottery/demo.html

Both pages are hidden from search engines (`noindex` + `robots.txt`), not in the sitemap and not linked from the site.

## How the draw works

- Every card number 100–1300 has **one fixed hidden draw number** (also 100–1300), made once as a random
  shuffle when you run Set up. No two cards share a draw number.
- **Half online, half printed.** Settings `online_from`–`online_to` (default 100–699) are sold on the page;
  the rest (700–1300) are printed scratch cards. The **Print tab** lists card number + scratch number for the printer.
- Online, a customer picks a card, enters name + phone, and the page reveals that card's fixed draw number.
  The card is then gone for everyone. Each phone number gets one card.
- On draw night, **Lottery → Find who holds a draw number** shows the card, whether it was sold online or
  printed, and the buyer.
- Once cards go to the printer, set Settings `numbers_locked` to TRUE so the numbers can never be regenerated.

## One-time setup (on a computer)

1. Create a new Google Sheet → **Extensions → Apps Script**.
2. Replace `Code.gs` with `Code.gs` from this folder. Save.
3. Reload the Sheet → **Lottery → Set up (first time) / clear online sales**, allow permissions. Card numbers, hidden draw numbers and the Print tab are created.
4. **Deploy → New deployment → Web app**, Execute as **Me**, Who has access **Anyone** → Deploy. Copy the URL (ends in `/exec`).
5. In `lottery/index.html`, paste that URL into `var API_URL = "";` and commit. The page goes live within a minute or two.

After changing `Code.gs`, use **Deploy → Manage deployments → Edit → New version** so the URL stays the same.

## Running the draw (all in the Sheet)

| Tab | What it holds |
|---|---|
| **Settings** | Range, online range, `open`, `require_code`, `draw_info` (date line on the page), `numbers_locked` |
| **Pool** | Every card: online or printed, its hidden draw number, sale status |
| **Print** | Printed cards only: card number + scratch number to print; fill Sold to / Phone / Notes as you sell |
| **Draws** | Online sales: card number, draw number, name, phone, time |
| **Log** | Every page visit, sale, repeat attempt, rejection, lookup and error, hash-chained so later edits are detectable |
| **Codes** | Optional one-time coupon codes |

**Lottery menu:** Find who holds a draw number · Run integrity check · Open / Close online sales ·
Generate coupon codes · Set up / clear online sales (keeps card numbers) · Generate new card numbers (before printing only).

The integrity check confirms every card has its own draw number and the list has not changed since it was made,
the Print tab matches, every online card was sold once, every phone bought once, and the log hash chain is unbroken.
