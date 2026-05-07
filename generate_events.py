import feedparser
import requests
from datetime import datetime, timezone, timedelta
import html
import re

# ── Timezone ──────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str   = now.strftime('%A, %d %B %Y')
time_str    = now.strftime('%I:%M %p IST')
date_short  = now.strftime('%d %B')
weekday     = now.strftime('%A').lower()
is_weekend  = now.weekday() >= 5

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

# ── Google News RSS feeds ─────────────────────────────────────────────────────
NEWS_FEEDS = [
    {'url': 'https://news.google.com/rss/search?q=kannur+festival+event+today&hl=en-IN&gl=IN&ceid=IN:en',          'area': 'Kannur',     'km': 0},
    {'url': 'https://news.google.com/rss/search?q=kannur+theyyam+kaliyattam+utsav&hl=en-IN&gl=IN&ceid=IN:en',     'area': 'Kannur',     'km': 0},
    {'url': 'https://news.google.com/rss/search?q=thalassery+festival+event&hl=en-IN&gl=IN&ceid=IN:en',           'area': 'Thalassery', 'km': 20},
    {'url': 'https://news.google.com/rss/search?q=kasaragod+event+festival+today&hl=en-IN&gl=IN&ceid=IN:en',      'area': 'Kasaragod',  'km': 55},
    {'url': 'https://news.google.com/rss/search?q=kozhikode+calicut+event+festival+today&hl=en-IN&gl=IN&ceid=IN:en','area': 'Kozhikode',  'km': 100},
    {'url': 'https://news.google.com/rss/search?q=wayanad+festival+event+today&hl=en-IN&gl=IN&ceid=IN:en',        'area': 'Wayanad',    'km': 105},
    {'url': 'https://news.google.com/rss/search?q=mangalore+event+festival+today&hl=en-IN&gl=IN&ceid=IN:en',      'area': 'Mangalore',  'km': 110},
    {'url': 'https://news.google.com/rss/search?q=kerala+festival+event+mela+today&hl=en-IN&gl=IN&ceid=IN:en',    'area': 'Kerala',     'km': 0},
    {'url': 'https://news.google.com/rss/search?q=north+kerala+malabar+festival+event&hl=en-IN&gl=IN&ceid=IN:en', 'area': 'Kannur',     'km': 0},
]

# ── Keywords that suggest an event is happening ───────────────────────────────
EVENT_KEYWORDS = [
    'festival', 'event', 'concert', 'exhibition', 'performance', 'show',
    'utsav', 'utsavam', 'mahotsavam', 'theyyam', 'thira', 'mela',
    'inauguration', 'celebration', 'programme', 'program', 'function',
    'ceremony', 'tournament', 'match', 'competition', 'expo', 'fair',
    'carnival', 'parade', 'procession', 'marathon', 'rally', 'yatra',
    'kaliyattam', 'pooram', 'ulsavam', 'seminar', 'workshop', 'conference',
    'inaugur', 'launch', 'meet', 'gathering', 'camp',
]

# Keywords that suggest it's happening NOW / TODAY
RECENCY_KEYWORDS = [
    'today', 'tonight', 'this evening', 'this morning', 'now on',
    'begins today', 'starts today', 'opening today', 'held today',
    'this weekend', 'this week', date_short, weekday,
]

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

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    return html.unescape(text).strip()

def is_event_article(title, desc):
    t = (title + ' ' + desc).lower()
    return any(k in t for k in EVENT_KEYWORDS)

def is_recent(entry):
    """True if article was published in the last 48 hours."""
    try:
        pub = entry.get('published_parsed') or entry.get('updated_parsed')
        if pub:
            pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
            age = now.astimezone(timezone.utc) - pub_dt
            return age.total_seconds() < 172800  # 48 hours
    except Exception:
        pass
    # Fallback: check for recency keywords in title/description
    t = (entry.get('title', '') + ' ' + entry.get('summary', '')).lower()
    return any(k in t for k in RECENCY_KEYWORDS)

def fetch_feed(url):
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
        return feedparser.parse(r.text)
    except Exception:
        return feedparser.parse(url)

# ── Fetch live event news ─────────────────────────────────────────────────────
def fetch_live_events():
    items = []
    seen  = set()

    for feed_info in NEWS_FEEDS:
        try:
            feed = fetch_feed(feed_info['url'])
            for entry in feed.entries[:15]:
                title = clean(entry.get('title', ''))
                desc  = clean(entry.get('summary', entry.get('description', '')))
                link  = entry.get('link', '#')

                if not title or title in seen:
                    continue
                if not is_event_article(title, desc):
                    continue
                if not is_recent(entry):
                    continue

                seen.add(title)
                items.append({
                    'title':  title,
                    'desc':   desc[:220] + '...' if len(desc) > 220 else desc,
                    'link':   link,
                    'area':   feed_info['area'],
                    'km':     feed_info['km'],
                    'source': feed.feed.get('title', 'News'),
                })
        except Exception as e:
            print(f"Error fetching {feed_info['area']}: {e}")

    # Sort by distance (Kannur first)
    items.sort(key=lambda x: x['km'])
    return items

# ── Render helpers ────────────────────────────────────────────────────────────
def km_badge(km):
    if km == 0:
        return '<span style="background:rgba(46,204,113,0.2);color:#2ecc71;font-size:0.65rem;padding:2px 8px;border-radius:10px;font-weight:700;">IN KANNUR</span>'
    return f'<span style="background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);font-size:0.65rem;padding:2px 8px;border-radius:10px;">{km} km away</span>'

def render_live_card(item):
    badge = km_badge(item['km'])
    return f'''
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:18px 20px;margin-bottom:14px;transition:border-color 0.2s;" onmouseover="this.style.borderColor='rgba(249,194,60,0.3)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.08)'">
      <a href="{item['link']}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
          <span style="font-size:0.68rem;color:var(--yellow);font-weight:700;letter-spacing:1px;text-transform:uppercase;">📌 {item['area']}</span>
          {badge}
        </div>
        <h3 style="font-family:'Playfair Display',serif;font-size:1.05rem;color:#fff;margin-bottom:8px;line-height:1.4;">{item['title']}</h3>
        <p style="font-size:0.85rem;color:rgba(255,255,255,0.5);line-height:1.6;margin-bottom:8px;">{item['desc']}</p>
        <span style="font-size:0.75rem;color:var(--orange);">Read more →</span>
      </a>
    </div>'''

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
def generate_html(live_items):
    weekend_emoji = "🎉" if is_weekend else "📅"
    weekend_label = "Weekend!" if is_weekend else "Weekday"

    live_html = ''.join(render_live_card(i) for i in live_items) if live_items else '''
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:32px;text-align:center;color:rgba(255,255,255,0.4);">
      <p style="font-size:1.1rem;margin-bottom:10px;">🔍 No specific events found for today in the news feeds.</p>
      <p style="font-size:0.9rem;">Check below for things you can always do in and around Kannur!</p>
    </div>'''

    highlights = [ev for ev in RECURRING if ev['star']]
    others     = [ev for ev in RECURRING if not ev['star']]
    recurring_html = ''.join(render_recurring_card(ev) for ev in highlights + others)

    kannur_count  = sum(1 for i in live_items if i['km'] == 0)
    nearby_count  = sum(1 for i in live_items if i['km'] > 0)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Events in Kannur Today — {today_str} | Travel Kannur</title>
<meta name="description" content="What's happening in Kannur today, {today_str}? Events, festivals, activities within 150 km of Kannur — updated every day.">
<meta name="keywords" content="Kannur events today, things to do Kannur, Kerala events today, Kannur festival today, Malabar events">
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
    <li><a href="news.html">News</a></li>
    <li><a href="theyyam.html">Theyyam</a></li>
    <li><a href="election_news.html">Elections</a></li>
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
    {today_str} — Events, festivals &amp; activities in Kannur and within 150 km
  </p>
  <p style="font-family:'Noto Sans Malayalam',sans-serif;color:var(--yellow);font-size:1rem;">കണ്ണൂരിൽ ഇന്ന് നടക്കുന്ന ഇവന്‍റുകൾ</p>

  <!-- Stats row -->
  <div style="display:flex;gap:32px;justify-content:center;flex-wrap:wrap;margin-top:36px;">
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{len(live_items)}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Live Events Found</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{kannur_count}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">In Kannur</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{nearby_count}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Nearby (&lt;150 km)</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Playfair Display',serif;font-size:2rem;color:var(--yellow);font-weight:900;">{weekend_emoji}</div>
      <div style="font-size:0.7rem;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-top:4px;">{weekend_label}</div>
    </div>
  </div>
</div>

<!-- AD -->
<div style="max-width:1100px;margin:24px auto;padding:0 5%;">
  <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>

<!-- MAIN GRID -->
<div style="max-width:1100px;margin:0 auto;padding:40px 5%;display:grid;grid-template-columns:3fr 2fr;gap:36px;" class="grid-2col">

  <!-- LEFT: LIVE EVENTS -->
  <div>
    <h2 style="font-family:'Playfair Display',serif;font-size:1.6rem;color:var(--yellow);margin-bottom:6px;">
      📰 In the News Today
    </h2>
    <p style="font-size:0.85rem;color:rgba(255,255,255,0.35);margin-bottom:24px;">Events &amp; festivals found in today's news — Kannur &amp; within 150 km</p>
    {live_html}

    <!-- AD mid -->
    <ins class="adsbygoogle" style="display:block;margin:24px 0;" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>

    <!-- DISTANCE NOTE -->
    <div style="background:rgba(249,194,60,0.05);border:1px solid rgba(249,194,60,0.15);border-radius:12px;padding:16px 20px;margin-top:8px;">
      <p style="font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.7;">
        <strong style="color:var(--yellow);">🗺️ Coverage area:</strong> Kannur district · Thalassery · Payyanur · Kasaragod (~55 km) · Kozhikode (~100 km) · Wayanad (~105 km) · Mangalore (~110 km) · Coorg (~130 km) · Thrissur (~145 km)
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

    <!-- SIDEBAR AD -->
    <ins class="adsbygoogle" style="display:block;margin-top:20px;" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
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
  <p>© 2026 <span style="color:var(--yellow);">TravelKannur.in</span> — <a href="index.html" style="color:var(--yellow);">← Home</a> · <a href="news.html" style="color:var(--yellow);">News</a> · <a href="theyyam.html" style="color:var(--yellow);">Theyyam</a></p>
  <p style="margin-top:6px;font-size:0.75rem;">Auto-updated daily. Events sourced from Google News RSS feeds. Always verify event details with the organiser before visiting.</p>
</footer>

<style>@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:0.5;transform:scale(1.4);}}}}</style>
<script src="https://travelkannur-chatbot.onrender.com/widget.js" data-server="https://travelkannur-chatbot.onrender.com"></script>
</body>
</html>'''

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"Fetching today's events for {today_str}...")
live_items = fetch_live_events()
print(f"Found {len(live_items)} live event articles")

page = generate_html(live_items)
with open('events.html', 'w', encoding='utf-8') as f:
    f.write(page)

print(f"✅ events.html generated at {time_str}")
