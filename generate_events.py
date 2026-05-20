from datetime import datetime, timezone, timedelta
import re

# ── Timezone ──────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str   = now.strftime('%A, %d %B %Y')
time_str    = now.strftime('%I:%M %p IST')
date_short  = now.strftime('%d %B')
weekday     = now.strftime('%A').lower()
is_weekend  = now.weekday() >= 5

# ── Kannur Carnival 2026 dates ────────────────────────────────────────────────
CARNIVAL_START = datetime(2026, 5, 1, tzinfo=IST)
CARNIVAL_END   = datetime(2026, 5, 31, 23, 59, tzinfo=IST)
carnival_active = CARNIVAL_START <= now <= CARNIVAL_END
if carnival_active:
    carnival_day = (now.date() - CARNIVAL_START.date()).days + 1
    carnival_days_left = (CARNIVAL_END.date() - now.date()).days
    carnival_status_label = f"Day {carnival_day} of 31 · {carnival_days_left} days left"
else:
    carnival_day = 0
    carnival_days_left = 0
    carnival_status_label = "1–31 May 2026"

# ── Areas within 150 km of Kannur ────────────────────────────────────────────
AREAS = [
    {'name': 'Kannur',     'km': 0,   'emoji': '📍', 'state': 'Kerala'},
    {'name': 'Thalassery', 'km': 20,  'emoji': '📍', 'state': 'Kerala'},
    {'name': 'Payyanur',   'km': 40,  'emoji': '📍', 'state': 'Kerala'},
    {'name': 'Kasaragod',  'km': 55,  'emoji': '🗺️', 'state': 'Kerala'},
    {'name': 'Kozhikode',  'km': 100, 'emoji': '🗺️', 'state': 'Kerala'},
    {'name': 'Wayanad',    'km': 105, 'emoji': '🗺️', 'state': 'Kerala'},
    {'name': 'Mangalore',  'km': 110, 'emoji': '🗺️', 'state': 'Karnataka'},
    {'name': 'Coorg',      'km': 130, 'emoji': '🗺️', 'state': 'Karnataka'},
    {'name': 'Thrissur',   'km': 145, 'emoji': '🗺️', 'state': 'Kerala'},
]

# ── (Events are now hand-curated by the editorial team — RSS scraping removed) ──

# ── Always-on / recurring attractions ────────────────────────────────────────
RECURRING = [
    {
        'name': 'Muthappan Theyyam',
        'ml':   'മുത്തപ്പൻ തെയ്യം',
        'loc':  'Sri Muthappan Temple, Parassinikkadavu',
        'area': 'Kannur', 'km': 18,
        'time': '6:30 AM & 6:30 PM every day',
        'cat':  'Theyyam 🔥',
        'emoji':'🔥',
        'desc': 'The only Theyyam performed daily year-round. Open to all visitors regardless of religion. Most accessible Theyyam in Kannur.',
        'link': 'https://travelkannur.in/theyyam.html',
        'star': True,
    },
    {
        'name': 'Payyambalam Beach',
        'ml':   'പയ്യാമ്പലം ബീച്ച്',
        'loc':  'Payyambalam, Kannur town',
        'area': 'Kannur', 'km': 0,
        'time': 'Always open | Best: 6–8 AM & 5–7 PM',
        'cat':  'Beach 🌊',
        'emoji':'🌊',
        'desc': 'Kannur\'s most popular beach with a wide sandy shore. Perfect for sunrise walks, sunset watching, and evening strolls.',
        'link': 'https://travelkannur.in/beaches.html',
        'star': False,
    },
    {
        'name': 'Muzhappilangad Drive-in Beach',
        'ml':   'മുഴപ്പിലങ്ങാട് ബീച്ച്',
        'loc':  'Muzhappilangad, Kannur',
        'area': 'Kannur', 'km': 15,
        'time': 'Always open | Best: Morning & Evening',
        'cat':  'Beach 🏖️',
        'emoji':'🏖️',
        'desc': 'Asia\'s longest drive-in beach — 4 km of flat sandy shore you can drive on. Unique experience near Kannur.',
        'link': 'https://travelkannur.in/beaches.html',
        'star': True,
    },
    {
        'name': 'Kavvayi Backwater Boat Ride',
        'ml':   'കവ്വായി കായൽ',
        'loc':  'Kavvayi, Payyannur',
        'area': 'Kannur', 'km': 40,
        'time': 'Boat rides: 7 AM – 5 PM',
        'cat':  'Nature / Water 🚤',
        'emoji':'🚤',
        'desc': 'Kerala\'s second largest backwater lake. Boat through mangroves, spot migratory birds, visit tiny island villages.',
        'link': 'https://travelkannur.in/backwaters.html',
        'star': False,
    },
    {
        'name': 'St. Angelo Fort',
        'ml':   'കണ്ണൂർ കോട്ട',
        'loc':  'Fort Road, Kannur town',
        'area': 'Kannur', 'km': 0,
        'time': '9 AM – 5:30 PM (closed Fridays)',
        'cat':  'Heritage 🏰',
        'emoji':'🏰',
        'desc': 'Portuguese fort built in 1505. Stunning sea views, historic bastions, and breezy clifftop walks. Free entry.',
        'link': '#',
        'star': False,
    },
    {
        'name': 'Arakkal Museum',
        'ml':   'അറക്കൽ മ്യൂസിയം',
        'loc':  'Arakkal Road, Kannur',
        'area': 'Kannur', 'km': 1,
        'time': '10 AM – 5 PM (closed Mondays)',
        'cat':  'Museum / Heritage 🏛️',
        'emoji':'🏛️',
        'desc': 'Museum of the only Muslim royal family in Kerala — the Arakkal royal dynasty. Artifacts, weapons, and royal history.',
        'link': '#',
        'star': False,
    },
    {
        'name': 'Kannur Handloom Weaving Experience',
        'ml':   'കണ്ണൂർ കൈത്തറി',
        'loc':  'Thottada & Chirakkal, Kannur',
        'area': 'Kannur', 'km': 5,
        'time': 'Mon–Sat: 9 AM – 5 PM',
        'cat':  'Culture / Craft 🧵',
        'emoji':'🧵',
        'desc': 'Visit working handloom weaving units — Kannur is Kerala\'s handloom capital. Watch artisans weave traditional fabrics.',
        'link': '#',
        'star': False,
    },
    {
        'name': 'Ezhimala — Naval Academy Hilltop',
        'ml':   'എഴിമല',
        'loc':  'Ezhimala, Payyanur (Kannur)',
        'area': 'Kannur', 'km': 38,
        'time': 'Open daily (civilian access to hill viewpoint)',
        'cat':  'Nature / Scenic 🏔️',
        'emoji':'🏔️',
        'desc': 'Sacred hilltop with Buddhist ruins, panoramic Arabian Sea views, and medicinal plant forests. One of Kerala\'s oldest historical sites.',
        'link': '#',
        'star': False,
    },
    {
        'name': 'Bekal Fort',
        'ml':   'ബേക്കൽ കോട്ട',
        'loc':  'Bekal, Kasaragod',
        'area': 'Kasaragod', 'km': 60,
        'time': '8 AM – 6 PM daily',
        'cat':  'Heritage / Beach 🏰',
        'emoji':'🏰',
        'desc': 'Kerala\'s largest fort, famous from Mani Ratnam\'s film. Keyhole-shaped with stunning backwater and sea views.',
        'link': '#',
        'star': True,
    },
    {
        'name': 'Wayanad Wildlife Sanctuary',
        'ml':   'വയനാട് വന്യജീവി സങ്കേതം',
        'loc':  'Muthanga, Wayanad',
        'area': 'Wayanad', 'km': 105,
        'time': 'Safari: 6 AM – 9 AM & 3 PM – 6 PM',
        'cat':  'Wildlife / Nature 🐘',
        'emoji':'🐘',
        'desc': 'Jeep safari through dense forests. Spot elephants, gaur, deer, and rare birds. Advance booking required.',
        'link': '#',
        'star': True,
    },
    {
        'name': 'Edakkal Caves',
        'ml':   'എടക്കൽ ഗുഹകൾ',
        'loc':  'Ambukuthi Hills, Wayanad',
        'area': 'Wayanad', 'km': 110,
        'time': '9 AM – 4:30 PM (closed Mondays)',
        'cat':  'Heritage / Trek 🪨',
        'emoji':'🪨',
        'desc': 'Ancient rock engravings from Neolithic era in a natural cleft in the mountain. 1-hour trek to reach them.',
        'link': '#',
        'star': False,
    },
]

# ── Render helpers ────────────────────────────────────────────────────────────

def km_badge(km):
    if km == 0:
        return '<span style="background:rgba(46,204,113,0.2);color:#2ecc71;font-size:0.65rem;padding:2px 8px;border-radius:10px;font-weight:700;">IN KANNUR</span>'
    return f'<span style="background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);font-size:0.65rem;padding:2px 8px;border-radius:10px;">{km} km away</span>'

def render_recurring_card(ev):
    badge  = km_badge(ev['km'])
    star   = '<span style="font-size:0.65rem;background:rgba(249,194,60,0.2);color:var(--yellow);padding:2px 8px;border-radius:10px;font-weight:700;margin-left:6px;">⭐ Highlight</span>' if ev['star'] else ''
    border = 'rgba(249,194,60,0.25)' if ev['star'] else 'rgba(255,255,255,0.07)'
    return f'''
    <div style="background:rgba(255,255,255,0.03);border:1px solid {border};border-radius:16px;padding:20px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
        <span style="font-size:1.4rem;">{ev['emoji']}</span>
        <span style="font-size:0.7rem;color:var(--orange);font-weight:700;letter-spacing:1px;text-transform:uppercase;">{ev['cat']}</span>
        {badge}{star}
      </div>
      <a href="{ev['link']}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;">
        <h3 style="font-family:'Playfair Display',serif;font-size:1.05rem;color:#fff;margin-bottom:4px;line-height:1.3;">{ev['name']}</h3>
        <p style="font-family:'Noto Sans Malayalam',sans-serif;font-size:0.8rem;color:rgba(249,194,60,0.6);margin-bottom:10px;">{ev['ml']}</p>
        <p style="font-size:0.82rem;color:rgba(255,255,255,0.45);margin-bottom:8px;">📍 {ev['loc']}</p>
        <p style="font-size:0.82rem;color:rgba(255,255,255,0.45);margin-bottom:10px;">🕐 {ev['time']}</p>
        <p style="font-size:0.85rem;color:rgba(255,255,255,0.6);line-height:1.6;">{ev['desc']}</p>
      </a>
    </div>'''

# ── Generate full HTML ────────────────────────────────────────────────────────
def generate_html():
    weekend_emoji = "🎉" if is_weekend else "📅"
    weekend_label = "Weekend!" if is_weekend else "Weekday"

    highlights = [ev for ev in RECURRING if ev['star']]
    others     = [ev for ev in RECURRING if not ev['star']]
    recurring_html = ''.join(render_recurring_card(ev) for ev in highlights + others)

    # Hero stat counters — featured carnival (1 while live) + 4 monthly highlights
    featured_count = 1 if carnival_active else 0
    monthly_highlights = 4  # Carnival, Theyyam finale, mango/jackfruit season, drive-in beach
    kannur_count  = featured_count + monthly_highlights
    nearby_count  = 0
    total_count   = featured_count + monthly_highlights

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="canonical" href="https://travelkannur.in/events.html">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"Events in Kannur","url":"https://travelkannur.in/events.html","description":"Editor-curated festivals, season highlights and ongoing happenings in Kannur, Kerala.","about":{{"@type":"TouristDestination","name":"Kannur","address":{{"@type":"PostalAddress","addressLocality":"Kannur","addressRegion":"Kerala","addressCountry":"IN"}}}}}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Festival","name":"Kannur Carnival 2026","alternateName":["Kannur Carnival","Kannur Fair"],"description":"Month-long carnival fair at Police Maidan, Kannur, running 1–31 May 2026 — amusement rides, food stalls, shopping bazaars, live entertainment, games and family activities.","startDate":"2026-05-01T17:00+05:30","endDate":"2026-05-31T23:00+05:30","location":{{"@type":"Place","name":"Police Maidan (Police Ground), Kannur","address":{{"@type":"PostalAddress","addressLocality":"Kannur","addressRegion":"Kerala","postalCode":"670001","addressCountry":"IN"}},"geo":{{"@type":"GeoCoordinates","latitude":11.8689,"longitude":75.3556}}}},"eventStatus":"https://schema.org/EventScheduled","eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode","url":"https://travelkannur.in/events.html#kannur-carnival","sameAs":"https://www.instagram.com/kannurcarnival2026/"}}</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kannur Carnival 2026 at Police Maidan &amp; Events in Kannur Today — {today_str} | Travel Kannur</title>
<meta name="description" content="Kannur Carnival 2026 runs 1–31 May at Police Maidan, Kannur — rides, food stalls, shopping, live entertainment. Editor-curated festivals and season highlights in Kannur ({today_str}).">
<meta name="keywords" content="Kannur Carnival, Kannur Carnival 2026, Kannur Carnival Police Maidan, Police Maidan Kannur, Kannur fair, Kannur city events, Kannur events today, things to do Kannur, Kerala events today, Kannur festival today, Malabar events, Kannur carnival Instagram">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6684797590545478" crossorigin="anonymous"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Raleway:wght@300;400;600;700&family=Noto+Sans+Malayalam:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root{{--orange:#F4650A;--yellow:#F9C23C;--green:#2ecc71;}}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'Raleway',sans-serif;background:#0f0f0f;color:#fff;overflow-x:hidden;}}
  nav{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:16px 5%;background:rgba(15,15,15,0.97);backdrop-filter:blur(10px);border-bottom:1px solid rgba(255,255,255,0.08);}}
  .nav-logo{{font-family:'Playfair Display',serif;font-size:1.4rem;color:var(--yellow);text-decoration:none;}}
  .nav-logo span{{color:var(--orange);}}
  .nav-links{{display:flex;gap:24px;list-style:none;}}
  .nav-links a{{color:rgba(255,255,255,0.6);text-decoration:none;font-size:0.8rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;}}
  .nav-links a:hover{{color:var(--yellow);}}
  @media(max-width:768px){{.nav-links{{display:none;}}.grid-2col{{grid-template-columns:1fr !important;}}}}
</style>
</head>
<body>

<nav>
  <a href="index.html" class="nav-logo">Travel<span>Kannur</span></a>
  <ul class="nav-links">
    <li><a href="index.html">Home</a></li>
    <li><a href="about.html">About</a></li>
    <li><a href="theyyam.html">Theyyam</a></li>
    <li><a href="beaches.html">Beaches</a></li>
  </ul>
</nav>

<!-- HERO -->
<div style="padding:110px 5% 60px;background:linear-gradient(135deg,#0f0f0f 0%,#0d1a0d 60%,#0f0f0f 100%);text-align:center;border-bottom:1px solid rgba(255,255,255,0.05);">
  <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(46,204,113,0.12);border:1px solid rgba(46,204,113,0.3);color:#2ecc71;font-size:0.7rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;padding:6px 18px;border-radius:30px;margin-bottom:20px;">
    <span style="width:8px;height:8px;background:#2ecc71;border-radius:50%;animation:pulse 1.5s infinite;display:inline-block;"></span>
    Updated {time_str}
  </div>
  <h1 style="font-family:'Playfair Display',serif;font-size:clamp(2.2rem,5vw,3.8rem);font-weight:900;color:#fff;line-height:1.1;margin-bottom:16px;">
    What's On in <span style="color:var(--yellow);">Kannur</span> Today
  </h1>
  <p style="color:rgba(255,255,255,0.55);font-size:1rem;max-width:540px;margin:0 auto 10px;line-height:1.7;">
    {today_str} — Editor's pick of festivals, season highlights and ongoing happenings in Kannur
  </p>
  <p style="font-family:'Noto Sans Malayalam',sans-serif;color:var(--yellow);font-size:1rem;">കണ്ണൂരിൽ ഇപ്പോൾ നടക്കുന്ന ഇവന്‍റുകൾ</p>

  <!-- Stats row -->
  <div style="display:flex;gap:32px;justify-content:center;flex-wrap:wrap;margin-top:36px;">
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{total_count}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Highlights this Month</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{kannur_count}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">In &amp; Around Kannur</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{weekend_emoji}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">{weekend_label}</div>
    </div>
  </div>
</div>

<!-- FEATURED EVENT: KANNUR CARNIVAL -->
<div id="kannur-carnival" style="max-width:1100px;margin:0 auto 40px;padding:0 5%;">
  <div style="background:linear-gradient(135deg,#3d1a0a 0%,#7a3b10 50%,#F4650A 100%);border-radius:24px;padding:40px;position:relative;overflow:hidden;box-shadow:0 20px 60px rgba(244,101,10,0.25);">
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:18px;">
      <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(46,204,113,0.95);color:#0f1a0f;font-size:0.7rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:6px 16px;border-radius:30px;">
        <span style="width:8px;height:8px;background:#0f1a0f;border-radius:50%;animation:pulse 1.5s infinite;display:inline-block;"></span>
        🎉 Happening Now in Kannur
      </div>
      <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.18);color:#fff;font-size:0.72rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:6px 16px;border-radius:30px;border:1px solid rgba(255,255,255,0.25);">
        📅 1–31 May 2026
      </div>
      <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(249,194,60,0.95);color:#3d1a0a;font-size:0.72rem;font-weight:800;letter-spacing:1px;text-transform:uppercase;padding:6px 16px;border-radius:30px;">
        ⏳ {carnival_status_label}
      </div>
    </div>
    <h2 style="font-family:'Playfair Display',serif;font-size:clamp(2rem,4.5vw,3.2rem);font-weight:900;color:#fff;line-height:1.1;margin-bottom:8px;">
      Kannur Carnival <span style="color:var(--yellow);">2026</span>
    </h2>
    <p style="font-family:'Noto Sans Malayalam',sans-serif;color:var(--yellow);font-size:1.1rem;margin-bottom:18px;">കണ്ണൂർ കാർണിവൽ 2026 — പോലീസ് മൈതാനത്ത്</p>
    <p style="color:rgba(255,255,255,0.92);font-size:1rem;line-height:1.75;margin-bottom:14px;max-width:760px;">
      <strong style="color:var(--yellow);">Kannur Carnival 2026</strong> is the big city fair running <strong>from 1 May to 31 May 2026</strong> at <strong>Police Maidan (Police Ground), Kannur</strong> — the city's main fairground right in the heart of town. A full month of amusement rides, food stalls, shopping, live entertainment and games for the whole family.
    </p>
    <p style="color:rgba(255,255,255,0.85);font-size:0.95rem;line-height:1.75;margin-bottom:18px;max-width:760px;">
      The carnival is a yearly highlight for people of Kannur and surrounding districts — a perfect evening out for families, students, couples and groups. Follow the official Instagram <a href="https://www.instagram.com/kannurcarnival2026/" target="_blank" rel="noopener" style="color:var(--yellow);font-weight:700;text-decoration:underline;">@kannurcarnival2026</a> for the latest schedule, performer line-ups and daily highlights.
    </p>

    <!-- INFO PILLS -->
    <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:24px;">
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">📍 Police Maidan, Kannur</span>
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">🗓️ 1–31 May 2026</span>
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">🕐 Evening &amp; night</span>
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">🎢 Rides &amp; games</span>
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">🚗 In Kannur city centre</span>
      <span style="background:rgba(0,0,0,0.35);color:#fff;font-size:0.82rem;padding:8px 14px;border-radius:30px;border:1px solid rgba(255,255,255,0.15);">👨‍👩‍👧 Family-friendly</span>
    </div>

    <!-- YOUTUBE VIDEOS — 2 col on desktop, stacked on mobile -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:24px;">

      <!-- Video 1: embed-disabled by uploader → clickable thumbnail card -->
      <div>
        <a href="https://www.youtube.com/watch?v=5cX1sgmkurM" target="_blank" rel="noopener" style="display:block;text-decoration:none;position:relative;width:100%;aspect-ratio:16/9;border-radius:14px;overflow:hidden;box-shadow:0 12px 36px rgba(0,0,0,0.4);background:#000;transition:transform 0.25s,box-shadow 0.25s;" onmouseover="this.style.transform='scale(1.01)';this.style.boxShadow='0 18px 48px rgba(244,101,10,0.45)'" onmouseout="this.style.transform='none';this.style.boxShadow='0 12px 36px rgba(0,0,0,0.4)'">
          <img src="https://img.youtube.com/vi/5cX1sgmkurM/maxresdefault.jpg" alt="Kannur Carnival 2026 — Police Maidan, Kannur" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.src='https://img.youtube.com/vi/5cX1sgmkurM/hqdefault.jpg'">
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:74px;height:74px;border-radius:50%;background:rgba(255,0,0,0.92);display:flex;align-items:center;justify-content:center;box-shadow:0 8px 24px rgba(0,0,0,0.5);">
            <div style="width:0;height:0;border-left:22px solid #fff;border-top:14px solid transparent;border-bottom:14px solid transparent;margin-left:5px;"></div>
          </div>
          <div style="position:absolute;bottom:12px;left:12px;background:rgba(0,0,0,0.78);color:#fff;font-size:0.72rem;font-weight:700;padding:5px 10px;border-radius:6px;display:flex;align-items:center;gap:6px;">
            <svg width="13" height="9" viewBox="0 0 24 17" fill="#FF0000" xmlns="http://www.w3.org/2000/svg"><path d="M23.5 2.6C23.2 1.5 22.4 0.7 21.3 0.4 19.4 0 12 0 12 0S4.6 0 2.7 0.4C1.6 0.7 0.8 1.5 0.5 2.6 0 4.5 0 8.5 0 8.5s0 4 0.5 5.9c0.3 1.1 1.1 1.9 2.2 2.2C4.6 17 12 17 12 17s7.4 0 9.3-0.4c1.1-0.3 1.9-1.1 2.2-2.2C24 12.5 24 8.5 24 8.5s0-4-0.5-5.9zM9.6 12.1V4.9l6.3 3.6-6.3 3.6z"/></svg>
            Watch on YouTube
          </div>
        </a>
        <p style="color:rgba(255,255,255,0.55);font-size:0.72rem;margin-top:6px;text-align:center;font-style:italic;">▶️ Kannur Carnival 2026 — clip 1</p>
      </div>

      <!-- Video 2: inline embed (oembed reported playable) — falls back gracefully if blocked -->
      <div>
        <div style="position:relative;width:100%;aspect-ratio:16/9;border-radius:14px;overflow:hidden;box-shadow:0 12px 36px rgba(0,0,0,0.4);background:#000;">
          <iframe src="https://www.youtube-nocookie.com/embed/YPmu6NjhsIg?rel=0&amp;modestbranding=1"
                  title="Kannur Carnival 2026 — News Tomorrow Kannur"
                  loading="lazy"
                  referrerpolicy="strict-origin-when-cross-origin"
                  allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen
                  style="position:absolute;inset:0;width:100%;height:100%;border:0;"></iframe>
        </div>
        <p style="color:rgba(255,255,255,0.55);font-size:0.72rem;margin-top:6px;text-align:center;font-style:italic;">▶️ Kannur Carnival 2026 — News Tomorrow Kannur</p>
      </div>

    </div>

    <!-- HIGHLIGHT TILES -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:24px;">
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🎡</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Amusement Rides</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Giant wheel, swings &amp; more</div>
      </div>
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🍢</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Food Stalls</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Malabar street food &amp; snacks</div>
      </div>
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🛍️</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Shopping Bazaars</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Clothes, toys, handicrafts</div>
      </div>
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🎤</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Live Entertainment</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Music, dance &amp; cultural shows</div>
      </div>
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🎯</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Games &amp; Stalls</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Carnival games, prize counters</div>
      </div>
      <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.12);border-radius:14px;padding:18px 14px;text-align:center;">
        <div style="font-size:2rem;line-height:1;margin-bottom:6px;">🤹</div>
        <div style="color:#fff;font-weight:700;font-size:0.85rem;">Kids' Zone</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.7rem;margin-top:2px;">Rides &amp; activities for children</div>
      </div>
    </div>

    <!-- HOW TO REACH -->
    <div style="background:rgba(0,0,0,0.3);border-radius:16px;padding:20px 24px;margin-bottom:20px;">
      <h3 style="color:var(--yellow);font-family:'Playfair Display',serif;font-size:1.15rem;margin-bottom:12px;">🚗 How to reach Police Maidan, Kannur</h3>
      <p style="color:rgba(255,255,255,0.85);font-size:0.9rem;line-height:1.75;">
        Police Maidan (also called Police Ground) is right in the centre of Kannur city — walking distance from KSRTC Bus Stand and a short auto-rickshaw ride from Kannur Railway Station (~2 km). From Kannur International Airport (CNN), it is about <strong>30 km / ~45 minutes by taxi</strong>. Visit in the evening when the fair is in full swing.
      </p>
    </div>

    <!-- TIPS -->
    <div style="background:rgba(0,0,0,0.3);border-radius:16px;padding:20px 24px;margin-bottom:20px;">
      <h3 style="color:var(--yellow);font-family:'Playfair Display',serif;font-size:1.15rem;margin-bottom:12px;">💡 Tips for visitors</h3>
      <ul style="list-style:none;padding:0;color:rgba(255,255,255,0.85);font-size:0.9rem;line-height:1.9;">
        <li>🕖 Best time to visit: <strong>after 6 PM</strong> — the fair really comes alive in the evening</li>
        <li>💵 Carry small cash for individual ride/game tickets and food stalls</li>
        <li>👟 Wear comfortable shoes — you'll be on your feet exploring</li>
        <li>🅿️ Parking can get crowded on weekends — consider an auto-rickshaw if you're nearby</li>
        <li>📱 Check <a href="https://www.instagram.com/kannurcarnival2026/" target="_blank" rel="noopener" style="color:var(--yellow);text-decoration:underline;">@kannurcarnival2026 on Instagram</a> for daily programme updates</li>
      </ul>
    </div>

    <!-- CTAs -->
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      <a href="https://www.instagram.com/kannurcarnival2026/" target="_blank" rel="noopener" style="background:var(--yellow);color:#3d1a0a;font-weight:800;padding:12px 24px;border-radius:30px;text-decoration:none;font-size:0.9rem;">📸 Follow @kannurcarnival2026</a>
      <a href="theyyam.html" style="background:rgba(255,255,255,0.15);color:#fff;font-weight:700;padding:12px 24px;border-radius:30px;text-decoration:none;font-size:0.9rem;border:1px solid rgba(255,255,255,0.2);">🔥 Theyyam Calendar</a>
      <a href="mailto:info@travelkannur.in?subject=Kannur Carnival 2026" style="background:rgba(255,255,255,0.15);color:#fff;font-weight:700;padding:12px 24px;border-radius:30px;text-decoration:none;font-size:0.9rem;border:1px solid rgba(255,255,255,0.2);">📧 Ask About the Carnival</a>
    </div>

    <p style="color:rgba(255,255,255,0.55);font-size:0.75rem;margin-top:16px;font-style:italic;">
      For exact dates, timings and the daily programme of Kannur Carnival 2026, please follow the official Instagram handle <a href="https://www.instagram.com/kannurcarnival2026/" target="_blank" rel="noopener" style="color:rgba(255,255,255,0.75);">@kannurcarnival2026</a>.
    </p>
  </div>
</div>

<!-- MAIN GRID -->
<div style="max-width:1100px;margin:0 auto;padding:40px 5%;display:grid;grid-template-columns:3fr 2fr;gap:36px;" class="grid-2col">

  <!-- LEFT: WHAT'S ON THIS MONTH (hand-curated by Travel Kannur editors) -->
  <div>
    <h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;color:var(--yellow);margin-bottom:6px;">
      🗓️ This Month in Kannur
    </h2>
    <p style="font-size:0.85rem;color:rgba(255,255,255,0.35);margin-bottom:24px;">Hand-picked happenings, season highlights and ongoing festivities in Kannur — curated by our editors.</p>

    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px 24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-size:1.3rem;">🎪</span>
        <span style="font-size:0.72rem;color:var(--orange);font-weight:700;letter-spacing:1px;text-transform:uppercase;">Top Pick of the Month</span>
      </div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;color:#fff;margin-bottom:6px;">Kannur Carnival at Police Maidan</h3>
      <p style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.7;">The biggest city fair of the year is on right now — rides, food stalls, live shows, kids' zone. See the featured section above for full details.</p>
      <a href="#kannur-carnival" style="display:inline-block;margin-top:10px;color:var(--yellow);font-size:0.82rem;font-weight:700;text-decoration:none;">↑ Jump to details</a>
    </div>

    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px 24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-size:1.3rem;">🔥</span>
        <span style="font-size:0.72rem;color:var(--orange);font-weight:700;letter-spacing:1px;text-transform:uppercase;">Theyyam Season Finale</span>
      </div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;color:#fff;margin-bottom:6px;">Closing Theyyams across Kannur</h3>
      <p style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.7;">May is the last chance to catch Theyyam before the monsoon. Maaniyoor Kizhakkekaav (23–25 May) closes the season this year. Our calendar has the full list.</p>
      <a href="theyyam.html" style="display:inline-block;margin-top:10px;color:var(--yellow);font-size:0.82rem;font-weight:700;text-decoration:none;">→ Theyyam calendar</a>
    </div>

    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px 24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-size:1.3rem;">🥭</span>
        <span style="font-size:0.72rem;color:var(--orange);font-weight:700;letter-spacing:1px;text-transform:uppercase;">In Season</span>
      </div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;color:#fff;margin-bottom:6px;">Malabar Mangoes &amp; Jackfruit</h3>
      <p style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.7;">May is peak season for North Kerala mangoes (Naattu Maanga, Kilichundan) and jackfruit. Any roadside stall in Kannur, Thalassery or Payyanur will have fresh fruit at unbeatable prices.</p>
    </div>

    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:22px 24px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-size:1.3rem;">🏖️</span>
        <span style="font-size:0.72rem;color:var(--orange);font-weight:700;letter-spacing:1px;text-transform:uppercase;">Drive-In Beach Season</span>
      </div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.15rem;color:#fff;margin-bottom:6px;">Last chance before the monsoon</h3>
      <p style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.7;">Muzhappilangad Drive-in Beach is at its best now — firm sand, calm sea. From June onwards the monsoon makes driving on the beach unsafe and the strip is usually closed to vehicles.</p>
      <a href="beaches.html" style="display:inline-block;margin-top:10px;color:var(--yellow);font-size:0.82rem;font-weight:700;text-decoration:none;">→ Beach guide</a>
    </div>

    <!-- DISTANCE NOTE -->
    <div style="background:rgba(249,194,60,0.05);border:1px solid rgba(249,194,60,0.15);border-radius:12px;padding:16px 20px;margin-top:18px;">
      <p style="font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.7;">
        <strong style="color:var(--yellow);">📝 Editor's note:</strong> Highlights on this page are hand-picked by our small editorial team. Have a festival, exhibition or community event we should feature? <a href="contact.html" style="color:var(--yellow);">Get in touch</a>.
      </p>
    </div>
  </div>

  <!-- RIGHT: ALWAYS ON -->
  <div>
    <h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;color:var(--yellow);margin-bottom:6px;">
      📍 Always On in Kannur
    </h2>
    <p style="font-size:0.85rem;color:rgba(255,255,255,0.35);margin-bottom:24px;">Things you can do today regardless of the date</p>
    {recurring_html}
  </div>
</div>

<!-- SHARE / LINKS -->
<div style="max-width:1100px;margin:0 auto 60px;padding:0 5%;">
  <div style="background:linear-gradient(135deg,#1a2e1a,#0f1a0f);border:1px solid rgba(46,204,113,0.2);border-radius:16px;padding:28px 32px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;">
    <div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.1rem;color:#fff;margin-bottom:4px;">📱 Share Today's Events</h3>
      <p style="color:rgba(255,255,255,0.6);font-size:0.85rem;">Let friends know what's on in Kannur!</p>
    </div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      <a href="https://wa.me/?text=Events+in+Kannur+Today+%E2%80%94+https%3A%2F%2Ftravelkannur.in%2Fevents.html" target="_blank" style="background:#25D366;color:#fff;padding:10px 20px;border-radius:30px;text-decoration:none;font-weight:700;font-size:0.85rem;">WhatsApp</a>
      <a href="theyyam.html" style="background:var(--orange);color:#fff;padding:10px 20px;border-radius:30px;text-decoration:none;font-weight:700;font-size:0.85rem;">🔥 Theyyam Calendar</a>
    </div>
  </div>
</div>

<footer style="background:#080808;color:rgba(255,255,255,0.3);text-align:center;padding:32px 5%;font-size:0.85rem;border-top:1px solid rgba(255,255,255,0.05);">
  <p>© 2026 <span style="color:var(--yellow);">TravelKannur.in</span> — <a href="index.html" style="color:var(--yellow);">Home</a> · <a href="theyyam.html" style="color:var(--yellow);">Theyyam</a> · <a href="about.html" style="color:var(--yellow);">About</a> · <a href="contact.html" style="color:var(--yellow);">Contact</a> · <a href="privacy.html" style="color:var(--yellow);">Privacy</a> · <a href="terms.html" style="color:var(--yellow);">Terms</a> · <a href="disclaimer.html" style="color:var(--yellow);">Disclaimer</a></p>
  <p style="margin-top:6px;font-size:0.75rem;">Highlights on this page are curated by the Travel Kannur editorial team. Always verify event details with the organiser before visiting.</p>
</footer>

<style>@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:0.5;transform:scale(1.4);}}}}</style>
<script src="https://travelkannur-chatbot.onrender.com/widget.js" data-server="https://travelkannur-chatbot.onrender.com"></script>
</body>
</html>'''

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"Rendering hand-curated events page for {today_str}...")

page = generate_html()
with open('events.html', 'w', encoding='utf-8') as f:
    f.write(page)

print(f"✅ events.html generated at {time_str}")

# ── Bump sitemap.xml lastmod for events.html (and other daily pages) ──────────
# Without this, Google sees the same lastmod every day and doesn't recrawl.
try:
    today_iso = now.strftime('%Y-%m-%d')
    with open('sitemap.xml', 'r', encoding='utf-8') as f:
        sitemap = f.read()
    # Update events.html lastmod to today
    sitemap = re.sub(
        r'(<loc>https://travelkannur\.in/events\.html</loc><lastmod>)[^<]+(</lastmod>)',
        rf'\g<1>{today_iso}\g<2>',
        sitemap
    )
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f"✅ sitemap.xml events.html lastmod bumped to {today_iso}")
except Exception as e:
    print(f"⚠️  sitemap update skipped: {e}")
