"""
Daily Kerala gold rate page generator.

Fetches spot gold price in INR from goldapi.io (free tier, 100 req/month),
computes 22K and 24K per-gram and per-pavan (8g) rates for Kerala, and
regenerates gold-rate.html.

Runs from GitHub Actions daily at ~9 AM IST. Reads API key from
environment variable GOLDAPI_KEY (set as GitHub Secret).

If the API call fails, the previous gold-rate.html is left untouched
so visitors still see the last known good rate with its own timestamp.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str = now.strftime('%A, %d %B %Y')
time_str = now.strftime('%I:%M %p IST')

API_KEY = os.environ.get('GOLDAPI_KEY', '').strip()
if not API_KEY:
    print("❌ GOLDAPI_KEY not set — skipping gold rate update")
    sys.exit(0)  # exit 0 so workflow doesn't fail; page stays as last version


def fetch_gold_price_inr():
    """Fetch current XAU/INR from goldapi.io. Returns dict or raises."""
    req = urllib.request.Request(
        'https://www.goldapi.io/api/XAU/INR',
        headers={
            'x-access-token': API_KEY,
            'Content-Type': 'application/json',
        }
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fmt(n):
    """Format as Indian rupees with thousand separators."""
    try:
        return f"₹{n:,.0f}"
    except Exception:
        return str(n)


def fmt2(n):
    try:
        return f"₹{n:,.2f}"
    except Exception:
        return str(n)


def render_page(data):
    """Render the gold-rate.html from fetched API data."""
    # goldapi.io response has price_gram_22k, price_gram_24k, price_gram_18k directly in INR
    g22 = data.get('price_gram_22k') or 0
    g24 = data.get('price_gram_24k') or 0
    g18 = data.get('price_gram_18k') or 0

    pavan_22 = g22 * 8
    pavan_24 = g24 * 8

    prev_close = data.get('prev_close_price') or 0
    price_per_oz = data.get('price') or 0
    change_pct = data.get('chp') or 0
    change_abs = data.get('ch') or 0
    change_arrow = '▲' if change_abs >= 0 else '▼'
    change_color = '#22c55e' if change_abs >= 0 else '#ef4444'
    change_bg = 'rgba(34,197,94,0.12)' if change_abs >= 0 else 'rgba(239,68,68,0.12)'
    change_word = 'up' if change_abs >= 0 else 'down'

    # Change in pavan 22K terms (24h)
    prev_close_g22 = prev_close / 31.1035 * (22/24) if prev_close else 0
    prev_pavan_22 = prev_close_g22 * 8
    pavan_change_abs = pavan_22 - prev_pavan_22

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="canonical" href="https://travelkannur.in/gold-rate.html">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kerala Gold Rate Today — 1 Pavan 22K Gold Price ({today_str}) | Travel Kannur</title>
<meta name="description" content="Today's gold rate in Kerala — 1 pavan (8g) 22K gold price for {today_str}. Live 22K &amp; 24K gold rates in Kannur, Kochi, Thiruvananthapuram. Updated daily 9 AM IST.">
<meta name="keywords" content="Kerala gold rate today, Kannur gold rate, pavan gold rate Kerala, 22K gold rate today, 24K gold rate, gold price Kerala {now.year}, kerala gold rate live">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6684797590545478" crossorigin="anonymous"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Raleway:wght@300;400;600;700&family=Noto+Sans+Malayalam:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root{{--orange:#F4650A;--yellow:#F9C23C;--deep:#1A0A00;--cream:#FFF8EE;--brown:#7A3B10;--light-orange:#FFE0C2;--gold:#D4AF37;}}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  html{{scroll-behavior:smooth;}}
  body{{font-family:'Raleway',sans-serif;background:var(--cream);color:#333;line-height:1.7;}}
  nav{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:16px 5%;background:rgba(26,10,0,0.95);backdrop-filter:blur(10px);}}
  .nav-logo{{font-family:'Playfair Display',serif;font-size:1.4rem;color:var(--yellow);text-decoration:none;}}
  .nav-logo span{{color:var(--orange);}}
  .nav-links{{display:flex;gap:22px;list-style:none;}}
  .nav-links a{{color:rgba(255,255,255,0.75);text-decoration:none;font-size:0.78rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;}}
  .nav-links a:hover{{color:var(--yellow);}}

  .hero{{background:linear-gradient(160deg,#1a0a00 0%,#7A3B10 60%,var(--gold) 100%);padding:130px 5% 70px;text-align:center;color:#fff;}}
  .hero .live-badge{{display:inline-flex;align-items:center;gap:8px;background:rgba(34,197,94,0.2);border:1px solid rgba(34,197,94,0.5);color:#22c55e;font-size:0.7rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;padding:6px 16px;border-radius:30px;margin-bottom:16px;}}
  .hero .live-badge span{{width:8px;height:8px;background:#22c55e;border-radius:50%;animation:pulse 1.5s infinite;}}
  .hero h1{{font-family:'Playfair Display',serif;font-size:clamp(2rem,5vw,3.4rem);color:#fff;margin-bottom:8px;}}
  .hero h1 span{{color:var(--yellow);}}
  .hero-ml{{font-family:'Noto Sans Malayalam',sans-serif;color:var(--yellow);font-size:1.05rem;margin-top:6px;}}
  .hero .date{{color:rgba(255,255,255,0.75);font-size:0.95rem;margin-top:12px;}}

  .main{{max-width:1000px;margin:-30px auto 0;padding:0 5% 60px;position:relative;z-index:5;}}

  .pavan-card{{background:#fff;border-radius:24px;padding:40px 32px;box-shadow:0 20px 60px rgba(122,59,16,0.18);border-top:5px solid var(--gold);text-align:center;margin-bottom:24px;}}
  .pavan-card .label{{font-size:0.72rem;color:var(--brown);font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:14px;}}
  .pavan-card .rate{{font-family:'Playfair Display',serif;font-size:clamp(2.6rem,7vw,4.6rem);font-weight:900;color:var(--deep);line-height:1.05;}}
  .pavan-card .small{{color:#666;font-size:0.9rem;margin-top:10px;}}
  .change-pill{{display:inline-flex;align-items:center;gap:6px;font-size:0.9rem;font-weight:700;padding:6px 14px;border-radius:20px;margin-top:14px;background:{change_bg};color:{change_color};}}

  .rates-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:32px;}}
  .rate-card{{background:#fff;border-radius:18px;padding:24px 22px;box-shadow:0 4px 20px rgba(122,59,16,0.06);border-left:4px solid var(--orange);}}
  .rate-card .type{{font-size:0.68rem;letter-spacing:2px;color:var(--brown);font-weight:700;text-transform:uppercase;margin-bottom:6px;}}
  .rate-card .amount{{font-family:'Playfair Display',serif;font-size:1.55rem;color:var(--deep);font-weight:900;}}
  .rate-card .per{{color:#888;font-size:0.85rem;margin-top:2px;}}

  .info-box{{background:#fff;border-radius:18px;padding:28px 32px;margin-bottom:24px;box-shadow:0 4px 20px rgba(122,59,16,0.06);}}
  .info-box h2{{font-family:'Playfair Display',serif;font-size:1.35rem;color:var(--deep);margin-bottom:12px;border-left:4px solid var(--gold);padding-left:14px;}}
  .info-box p{{color:#555;margin-bottom:10px;font-size:0.95rem;}}
  .info-box ul{{margin:8px 0 0 22px;color:#555;font-size:0.92rem;}}
  .info-box li{{margin-bottom:6px;}}

  .disclaimer{{background:rgba(249,194,60,0.12);border:1px solid rgba(249,194,60,0.35);border-radius:14px;padding:20px 24px;font-size:0.88rem;color:#7A3B10;line-height:1.7;}}
  .disclaimer strong{{color:var(--brown);}}

  .attrib{{text-align:center;color:#999;font-size:0.78rem;margin-top:14px;font-style:italic;}}
  .attrib a{{color:#999;}}

  footer{{background:var(--deep);color:rgba(255,255,255,0.45);text-align:center;padding:32px 5%;font-size:0.82rem;}}
  footer a{{color:var(--yellow);text-decoration:none;margin:0 4px;}}
  footer span{{color:var(--yellow);}}

  @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:0.4;transform:scale(1.5);}}}}
  @media(max-width:768px){{.nav-links{{display:none;}}}}
</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"Kerala Gold Rate Today","url":"https://travelkannur.in/gold-rate.html","description":"Today's gold rate in Kerala — 1 pavan (8g) 22K, per-gram 22K and 24K rates. Updated daily from goldapi.io spot price.","inLanguage":"en","dateModified":"{now.strftime('%Y-%m-%dT%H:%M:%S+05:30')}"}}</script>
</head>
<body>

<nav>
  <a href="index.html" class="nav-logo">Travel<span>Kannur</span></a>
  <ul class="nav-links">
    <li><a href="index.html">Home</a></li>
    <li><a href="theyyam.html">🔥 Theyyam</a></li>
    <li><a href="beaches.html">Beaches</a></li>
    <li><a href="events.html">📅 Events</a></li>
    <li><a href="about.html">About</a></li>
    <li><a href="contact.html">Contact</a></li>
  </ul>
</nav>

<div class="hero">
  <div class="live-badge"><span></span>Updated {time_str}</div>
  <h1>Kerala <span>Gold Rate</span> Today</h1>
  <p class="hero-ml">കേരള സ്വർണവില — ഇന്ന്</p>
  <p class="date">{today_str}</p>
</div>

<div class="main">

  <!-- HERO PAVAN CARD -->
  <div class="pavan-card">
    <div class="label">🪙 1 Pavan (8 g) · 22 K Gold</div>
    <div class="rate">{fmt(pavan_22)}</div>
    <div class="small">Kerala &amp; Kannur reference rate · derived from international spot price</div>
    <div class="change-pill">{change_arrow} {abs(change_pct):.2f}% ({fmt2(abs(pavan_change_abs))} per pavan) in 24 h</div>
  </div>

  <!-- RATES BREAKDOWN -->
  <div class="rates-grid">
    <div class="rate-card">
      <div class="type">22 K Gold</div>
      <div class="amount">{fmt2(g22)}</div>
      <div class="per">per gram</div>
    </div>
    <div class="rate-card">
      <div class="type">24 K Gold</div>
      <div class="amount">{fmt2(g24)}</div>
      <div class="per">per gram</div>
    </div>
    <div class="rate-card">
      <div class="type">18 K Gold</div>
      <div class="amount">{fmt2(g18)}</div>
      <div class="per">per gram</div>
    </div>
    <div class="rate-card">
      <div class="type">1 Pavan · 24 K</div>
      <div class="amount">{fmt(pavan_24)}</div>
      <div class="per">8 grams pure gold</div>
    </div>
  </div>

  <!-- WHAT IS A PAVAN -->
  <div class="info-box">
    <h2>What is a pavan?</h2>
    <p>In Kerala, gold is traditionally traded and priced in <strong>pavan</strong> (Malayalam: <span class="hero-ml" style="font-size:1em;color:var(--brown);">പവൻ</span>). One pavan equals <strong>8 grams</strong> of 22-carat gold — the standard weight for a Kerala wedding chain, chunky bangles, or a heavy pendant.</p>
    <ul>
      <li>1 pavan = 8 grams (22 K by convention)</li>
      <li>Also called <em>pounu</em> or <em>sovereign</em> in older usage</li>
      <li>Displayed rates are for the metal only — jewellery adds making charges and GST on top</li>
    </ul>
  </div>

  <!-- DISCLAIMER -->
  <div class="disclaimer">
    <strong>💡 Please note:</strong> The rates on this page are derived from the <strong>international spot gold price</strong> in INR (from goldapi.io) and represent the pure-metal reference value. Actual jewellery-shop prices in Kannur / Kochi / Thiruvananthapuram will typically be <strong>higher</strong> because they include <strong>making charges (5–25 %)</strong>, <strong>wastage</strong>, and <strong>3 % GST</strong>. Local jewellery associations may also publish a slightly different "association rate" each morning. Always confirm the exact rate with your jeweller before purchase.
  </div>

  <p class="attrib">Data source: <a href="https://www.goldapi.io" target="_blank" rel="noopener">goldapi.io</a> · Refreshed daily at 9 AM IST</p>

</div>

<footer>
  <p>© {now.year} <span>TravelKannur.in</span> — <a href="index.html">Home</a>·<a href="theyyam.html">Theyyam</a>·<a href="beaches.html">Beaches</a>·<a href="events.html">Events</a>·<a href="gold-rate.html">Gold Rate</a>·<a href="about.html">About</a>·<a href="contact.html">Contact</a>·<a href="privacy.html">Privacy</a>·<a href="terms.html">Terms</a>·<a href="disclaimer.html">Disclaimer</a></p>
  <p style="margin-top:6px;font-size:0.75rem;">Gold rates are for reference only — not financial advice. Confirm actual purchase rates with your jeweller.</p>
</footer>

</body>
</html>
"""


def main():
    try:
        data = fetch_gold_price_inr()
    except urllib.error.HTTPError as e:
        print(f"❌ API HTTPError {e.code}: {e.read().decode('utf-8', errors='ignore')[:200]}")
        sys.exit(0)  # leave existing page intact
    except Exception as e:
        print(f"❌ API error: {e}")
        sys.exit(0)

    if not data.get('price'):
        print(f"❌ Unexpected API response: {data}")
        sys.exit(0)

    print(f"✅ Fetched gold @ {data.get('price'):.2f} INR/oz  (22K/g = {data.get('price_gram_22k'):.2f})")

    html = render_page(data)
    with open('gold-rate.html', 'w', encoding='utf-8') as f:
        f.write(html)

    # Also emit a compact JSON for embedding as a widget elsewhere
    widget = {
        'ts': now.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
        'pavan_22k_inr': round((data.get('price_gram_22k') or 0) * 8, 2),
        'gram_22k_inr': round(data.get('price_gram_22k') or 0, 2),
        'gram_24k_inr': round(data.get('price_gram_24k') or 0, 2),
        'change_pct_24h': round(data.get('chp') or 0, 3),
        'source': 'goldapi.io',
    }
    with open('gold-rate.json', 'w', encoding='utf-8') as f:
        json.dump(widget, f, indent=2)

    print(f"✅ gold-rate.html generated at {time_str}")

    # Bump sitemap lastmod so Google recrawls
    try:
        import re
        today_iso = now.strftime('%Y-%m-%d')
        with open('sitemap.xml', 'r', encoding='utf-8') as f:
            sm = f.read()
        if 'gold-rate.html' in sm:
            sm = re.sub(
                r'(<loc>https://travelkannur\.in/gold-rate\.html</loc><lastmod>)[^<]+(</lastmod>)',
                rf'\g<1>{today_iso}\g<2>',
                sm,
            )
            with open('sitemap.xml', 'w', encoding='utf-8') as f:
                f.write(sm)
            print(f"✅ sitemap.xml gold-rate.html lastmod bumped to {today_iso}")
    except Exception as e:
        print(f"⚠️  sitemap update skipped: {e}")


if __name__ == '__main__':
    main()
