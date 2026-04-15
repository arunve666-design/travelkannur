import feedparser
import requests
from datetime import datetime, timezone, timedelta
import html
import re

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)
today_str = now.strftime('%A, %d %B %Y')
time_str = now.strftime('%I:%M %p IST')

# RSS Feeds — mix of national and Kerala sources
FEEDS = [
    {
        'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCqCH1uDvmbPOpBBxcGBooxw',
        'source': 'Kannur Vision',
        'emoji': '📡',
        'force_include': True,
        'force_kannur': True,
    },
    {
        'url': 'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',
        'source': 'Times of India Kerala',
        'emoji': '🗞️'
    },
    {
        'url': 'https://www.thehindu.com/news/national/kerala/?service=rss',
        'source': 'The Hindu Kerala',
        'emoji': '📰'
    },
    {
        'url': 'https://feeds.feedburner.com/ndtvnews-south',
        'source': 'NDTV South',
        'emoji': '📺'
    },
    {
        'url': 'https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms',
        'source': 'Times of India India',
        'emoji': '🗞️'
    },
    {
        'url': 'https://www.thehindu.com/elections/?service=rss',
        'source': 'The Hindu Elections',
        'emoji': '📰'
    },
]

ELECTION_KEYWORDS = [
    'election', 'elections', 'vote', 'voting', 'ballot', 'candidate', 'constituency',
    'eci', 'poll', 'polls', 'polling', 'campaign', 'campaigning',
    'bjp', 'congress', 'cpim', 'udf', 'ldf', 'nda', 'upa',
    'mp', 'mla', 'assembly', 'lok sabha', 'rajya sabha',
    'seat', 'seats', 'manifesto', 'bypolls', 'by-election', 'by election',
    'electoral', 'electorate', 'voter', 'voters', 'turnout',
    'result', 'results', 'winner', 'defeat', 'victory',
    'nomination', 'nominee', 'party', 'alliance',
    'kannur constituency', 'kerala election', 'kerala vote',
    'pinarayi', 'opposition leader', 'chief minister', 'cm candidate',
]

KANNUR_KEYWORDS = ['kannur', 'malabar', 'thalassery', 'payyanur', 'iritty', 'north kerala']


def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text or '')
    text = html.unescape(text)
    return text.strip()


def is_election(title, desc):
    t = (title + ' ' + desc).lower()
    return any(k in t for k in ELECTION_KEYWORDS)


def is_kannur(title, desc):
    t = (title + ' ' + desc).lower()
    return any(k in t for k in KANNUR_KEYWORDS)


def fetch_feed(url):
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'}, verify=False)
        return feedparser.parse(r.text)
    except Exception:
        return feedparser.parse(url)

def fetch_election_news():
    all_items = []
    for feed_info in FEEDS:
        try:
            feed = fetch_feed(feed_info['url'])
            for entry in feed.entries[:20]:
                title = clean_html(entry.get('title', ''))
                desc = clean_html(entry.get('summary', entry.get('description', '')))
                link = entry.get('link', '#')
                img = ''
                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    img = entry.media_thumbnail[0].get('url', '')
                elif hasattr(entry, 'media_content') and entry.media_content:
                    img = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    img = entry.enclosures[0].get('href', '')

                # force_include means include all videos (e.g. Kannur Vision)
                if title and (feed_info.get('force_include') or is_election(title, desc)):
                    all_items.append({
                        'title': title,
                        'desc': desc[:200] + '...' if len(desc) > 200 else desc,
                        'link': link,
                        'img': img,
                        'source': feed_info['source'],
                        'emoji': feed_info['emoji'],
                        'is_kannur': feed_info.get('force_kannur', False) or is_kannur(title, desc),
                    })
        except Exception as e:
            print(f"Error fetching {feed_info['source']}: {e}")

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)
    return unique


def render_featured(item):
    kannur_badge = '<span style="background:rgba(244,101,10,0.2);color:#F4650A;font-size:0.65rem;padding:2px 8px;border-radius:10px;margin-left:8px;font-weight:700;">KANNUR</span>' if item['is_kannur'] else ''
    img_html = (
        f'<img style="width:100%;height:220px;object-fit:cover;" src="{item["img"]}" '
        f'alt="{html.escape(item["title"])}" onerror="this.parentElement.style.display=\'none\'">'
        if item['img'] else
        '<div style="width:100%;height:160px;background:linear-gradient(135deg,rgba(26,82,26,0.3),rgba(244,101,10,0.05));'
        'display:flex;align-items:center;justify-content:center;font-size:3rem;">🗳️</div>'
    )
    return f'''
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;margin-bottom:24px;transition:border-color 0.3s;">
      <a href="{item['link']}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;display:block;">
        {img_html}
        <div style="padding:24px;">
          <p style="font-size:0.7rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#F4650A;margin-bottom:8px;">{item['emoji']} {item['source']}{kannur_badge}</p>
          <h2 style="font-family:'Playfair Display',serif;font-size:1.3rem;color:#fff;margin-bottom:10px;line-height:1.4;">{item['title']}</h2>
          <p style="font-size:0.9rem;color:rgba(255,255,255,0.55);line-height:1.7;margin-bottom:14px;">{item['desc']}</p>
          <span style="color:#F4650A;font-weight:700;font-size:0.82rem;">Read Full Story →</span>
        </div>
      </a>
    </div>'''


def render_small(item):
    kannur_badge = '<span style="background:rgba(244,101,10,0.2);color:#F4650A;font-size:0.62rem;padding:2px 6px;border-radius:8px;margin-left:6px;font-weight:700;">KANNUR</span>' if item['is_kannur'] else ''
    return f'''
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px;margin-bottom:14px;">
      <a href="{item['link']}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;">
        <p style="font-size:0.68rem;color:#F4650A;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">{item['emoji']} {item['source']}{kannur_badge}</p>
        <h3 style="font-family:'Playfair Display',serif;font-size:1rem;color:#fff;margin-bottom:8px;line-height:1.4;">{item['title']}</h3>
        <p style="font-size:0.82rem;color:rgba(255,255,255,0.5);line-height:1.6;margin-bottom:8px;">{item['desc']}</p>
        <span style="font-size:0.72rem;color:rgba(255,255,255,0.3);">Read full story →</span>
      </a>
    </div>'''


def generate_html(items):
    # Kannur-specific election news first
    kannur_items = [i for i in items if i['is_kannur']]
    general_items = [i for i in items if not i['is_kannur']]
    sorted_items = kannur_items + general_items

    featured = sorted_items[:3]
    rest = sorted_items[3:13]

    featured_html = ''.join(render_featured(i) for i in featured)
    rest_html = ''.join(render_small(i) for i in rest)

    if not sorted_items:
        featured_html = '''<div style="background:rgba(244,101,10,0.08);border:1px solid rgba(244,101,10,0.2);border-radius:12px;padding:32px;text-align:center;color:rgba(255,255,255,0.6);">
          <p style="font-size:1.1rem;margin-bottom:12px;">🗳️ No election news found right now</p>
          <p>Check back during election season or read general Kerala news at <a href="news.html" style="color:#F4650A;">Kannur News</a></p>
        </div>'''

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kerala Election News {now.strftime('%Y')} — Kannur Election Updates | Travel Kannur</title>
<meta name="description" content="Latest Kerala and Kannur election news for {today_str}. Lok Sabha, Assembly, and local body election updates from Kannur district — updated daily.">
<meta name="keywords" content="Kerala election news, Kannur election 2026, Kerala polls, Lok Sabha Kerala, Assembly election Kerala, Kerala election results">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6684797590545478" crossorigin="anonymous"></script>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Raleway:wght@300;400;600&family=Noto+Sans+Malayalam:wght@400;700&display=swap" rel="stylesheet">
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
  @media(max-width:768px){{.nav-links{{display:none;}}.news-grid{{grid-template-columns:1fr !important;}}}}
</style>
</head>
<body>
<nav>
  <a href="index.html" class="nav-logo">Travel<span>Kannur</span></a>
  <ul class="nav-links">
    <li><a href="index.html">Home</a></li>
    <li><a href="news.html">News</a></li>
    <li><a href="theyyam.html">Theyyam</a></li>
    <li><a href="beaches.html">Beaches</a></li>
  </ul>
</nav>

<!-- HERO -->
<div style="padding:110px 5% 50px;background:linear-gradient(135deg,#0f0f0f,#001a00);text-align:center;">
  <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(46,204,113,0.12);border:1px solid rgba(46,204,113,0.3);color:#2ecc71;font-size:0.7rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;padding:6px 18px;border-radius:30px;margin-bottom:20px;">
    <span style="width:8px;height:8px;background:#2ecc71;border-radius:50%;animation:pulse 1.5s infinite;display:inline-block;"></span>
    Updated {time_str}
  </div>
  <h1 style="font-family:'Playfair Display',serif;font-size:clamp(2.5rem,5vw,4rem);font-weight:900;color:#fff;line-height:1.1;margin-bottom:16px;">Kerala <span style="color:var(--yellow);">Election</span> News</h1>
  <p style="color:rgba(255,255,255,0.55);font-size:1rem;max-width:520px;margin:0 auto 8px;line-height:1.7;">{today_str} — Kannur & Kerala election coverage, polls, results, and political updates</p>
  <p style="font-family:'Noto Sans Malayalam',sans-serif;color:var(--yellow);font-size:1rem;">കേരള തിരഞ്ഞെടുപ്പ് വാർത്തകൾ</p>
</div>

<!-- AD -->
<div style="max-width:1100px;margin:20px auto;padding:0 5%;">
  <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>

<!-- NEWS GRID -->
<div style="max-width:1100px;margin:0 auto;padding:40px 5%;display:grid;grid-template-columns:2fr 1fr;gap:32px;" class="news-grid">

  <!-- MAIN -->
  <div>
    {featured_html}
    <!-- AD -->
    <ins class="adsbygoogle" style="display:block;margin:24px 0;" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    {rest_html}
  </div>

  <!-- SIDEBAR -->
  <div>
    <!-- ELECTION INFO BOX -->
    <div style="background:rgba(46,204,113,0.06);border:1px solid rgba(46,204,113,0.15);border-radius:16px;padding:24px;margin-bottom:20px;">
      <h3 style="font-family:'Playfair Display',serif;color:#2ecc71;margin-bottom:16px;font-size:1rem;padding-bottom:12px;border-bottom:1px solid rgba(46,204,113,0.15);">🗳️ Key Links</h3>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="https://eci.gov.in" target="_blank" rel="noopener" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">🏛️ Election Commission of India</a></div>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="https://ceokerala.gov.in" target="_blank" rel="noopener" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">📋 CEO Kerala — Voter Info</a></div>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="https://voters.eci.gov.in" target="_blank" rel="noopener" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">✅ Check Voter Registration</a></div>
      <div style="padding:10px 0;"><a href="news.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">📰 General Kannur News</a></div>
    </div>
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:24px;margin-bottom:20px;">
      <h3 style="font-family:'Playfair Display',serif;color:var(--yellow);margin-bottom:16px;font-size:1rem;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.08);">📌 Explore Kannur</h3>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="theyyam.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">🔥 Theyyam Calendar 2025–26</a></div>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="beachtoday.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">🌊 Best Beach Today</a></div>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="beaches.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">🏖️ Top 5 Beaches in Kannur</a></div>
      <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><a href="backwaters.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">🚤 Kavvayi Backwaters</a></div>
      <div style="padding:10px 0;"><a href="hillstations.html" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:0.88rem;">⛰️ Hill Stations</a></div>
    </div>
    <!-- SIDEBAR AD -->
    <ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6684797590545478" data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    <!-- HOTEL BOOKING -->
    <div style="background:linear-gradient(135deg,rgba(244,101,10,0.1),rgba(122,59,16,0.15));border:1px solid rgba(244,101,10,0.2);border-radius:16px;padding:24px;margin-top:20px;">
      <h3 style="font-family:'Playfair Display',serif;color:var(--yellow);margin-bottom:12px;font-size:1rem;">🏨 Book Hotels in Kannur</h3>
      <a href="https://www.booking.com/searchresults.html?ss=Kannur+Kerala+India" target="_blank" rel="noopener" style="display:block;background:#F4650A;color:#fff;text-align:center;padding:12px;border-radius:10px;text-decoration:none;font-weight:700;font-size:0.88rem;margin-bottom:10px;">🌐 Booking.com</a>
      <a href="https://www.makemytrip.com/hotels/hotel-listing/?city=Kannur&country=IN" target="_blank" rel="noopener" style="display:block;background:#e8192c;color:#fff;text-align:center;padding:12px;border-radius:10px;text-decoration:none;font-weight:700;font-size:0.88rem;">✈️ MakeMyTrip</a>
    </div>
  </div>
</div>

<!-- SHARE -->
<div style="max-width:1100px;margin:0 auto 60px;padding:0 5%;">
  <div style="background:linear-gradient(135deg,#1a4a2e,#0f2d1a);border:1px solid rgba(46,204,113,0.2);border-radius:16px;padding:28px 32px;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;">
    <div>
      <h3 style="font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;margin-bottom:4px;">🗳️ Share Kerala Election News</h3>
      <p style="color:rgba(255,255,255,0.7);font-size:0.85rem;">Keep your friends informed about elections in Kerala!</p>
    </div>
    <a href="https://wa.me/?text=Kerala%20Election%20News%20-%20https://travelkannur.in/election_news.html" target="_blank" style="background:#25D366;color:#fff;padding:12px 24px;border-radius:30px;text-decoration:none;font-weight:700;font-size:0.88rem;">📱 Share on WhatsApp</a>
  </div>
</div>

<footer style="background:#080808;color:rgba(255,255,255,0.3);text-align:center;padding:32px 5%;font-size:0.85rem;border-top:1px solid rgba(255,255,255,0.05);">
  <p>© 2026 <span style="color:var(--yellow);">TravelKannur.in</span> — <a href="index.html" style="color:var(--yellow);">← Home</a> · <a href="news.html" style="color:var(--yellow);">Kannur News</a></p>
  <p style="margin-top:6px;font-size:0.75rem;">Auto-updated daily at 8:00 AM IST. News content belongs to respective publishers.</p>
</footer>

<style>@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:0.5;transform:scale(1.4);}}}}</style>
</body>
</html>'''
    return page


# Main
print("Fetching election news...")
items = fetch_election_news()
print(f"Fetched {len(items)} election news items")

html_content = generate_html(items)

with open('election_news.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ election_news.html generated successfully at {time_str}")
