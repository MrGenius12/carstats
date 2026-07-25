"""
CarStats.ie — Insights generator

Builds the /insights/ section from Markdown posts:
  - /insights/                 index page (list of all posts)
  - /insights/<slug>/          one page per post

Run alongside the existing generate.py. Same visual language as the
rest of the site (dark theme, header/footer/nav, breadcrumbs, per-page SEO).

Usage:
    pip install python-frontmatter markdown
    python generate_insights.py

Content:
    Add a new .md file to content/insights/ for each post. Frontmatter fields:

    title        (required) page <title> / <h1>
    slug         (required) URL segment -> /insights/<slug>/
    date         (required) YYYY-MM-DD, shown on cards and post page
    description  (required) meta description / og:description / intro line
    video_type   "file" (self-hosted <video>) or "youtube" (embedded iframe)
    video_src    file: path under /media/insights/...  |  youtube: video ID or full URL
    video_poster path to a poster/thumbnail image (used as og:image + card image + <video poster>)
    og_image     optional override for og:image (defaults to video_poster)
    tags         optional list of short tags shown on the card and post page

    Body is Markdown, rendered as the article commentary.
"""

import os
import re
import frontmatter
import markdown as md
from datetime import datetime

SITE_ROOT   = "https://carstats.ie"
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content", "insights")
OUTPUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "insights")

# ── Shared chrome (header / nav / footer / cookie banner) ──────────────────
# Kept in one place so both the list page and post pages stay in sync with
# the rest of the site. If generate.py already holds a shared template for
# this, swap these strings out for that template instead of duplicating.

LOGO_SVG = '''<svg width="153" height="40" viewBox="0 0 153 40" xmlns="http://www.w3.org/2000/svg">
<g fill="#F5F7FA">
<path transform="translate(0,29) scale(0.03,-0.03)" d="M392 704Q503 704 589.5 649.5Q676 595 715 495H578Q551 550 503.0 577.0Q455 604 392 604Q323 604 269.0 573.0Q215 542 184.5 484.0Q154 426 154 349Q154 272 184.5 214.0Q215 156 269.0 124.5Q323 93 392 93Q455 93 503.0 120.0Q551 147 578 202H715Q676 102 589.5 48.0Q503 -6 392 -6Q294 -6 213.0 39.5Q132 85 84.5 166.0Q37 247 37 349Q37 451 84.5 532.0Q132 613 213.5 658.5Q295 704 392 704Z"/>
<path transform="translate(23.189999999999998,29) scale(0.03,-0.03)" d="M297 560Q362 560 410.5 534.5Q459 509 488 471V551H603V0H488V82Q459 43 409.0 17.0Q359 -9 295 -9Q224 -9 165.0 27.5Q106 64 71.5 129.5Q37 195 37 278Q37 361 71.5 425.0Q106 489 165.5 524.5Q225 560 297 560ZM321 461Q277 461 239.0 439.5Q201 418 177.5 376.5Q154 335 154 278Q154 221 177.5 178.0Q201 135 239.5 112.5Q278 90 321 90Q365 90 403.0 112.0Q441 134 464.5 176.5Q488 219 488 276Q488 333 464.5 375.0Q441 417 403.0 439.0Q365 461 321 461Z"/>
<path transform="translate(43.53,29) scale(0.03,-0.03)" d="M354 560V442H325Q258 442 223.5 408.0Q189 374 189 290V0H75V551H189V471Q214 513 255.5 536.5Q297 560 354 560Z"/>
</g>
<g fill="#4F8CFF">
<path transform="translate(55.05,29) scale(0.03,-0.03)" d="M58 192H180Q184 147 215.5 118.0Q247 89 304 89Q363 89 396.0 117.5Q429 146 429 191Q429 226 408.5 248.0Q388 270 357.5 282.0Q327 294 273 308Q205 326 162.5 344.5Q120 363 90.0 402.0Q60 441 60 506Q60 566 90.0 611.0Q120 656 174.0 680.0Q228 704 299 704Q400 704 464.5 653.5Q529 603 536 515H410Q407 553 374.0 580.0Q341 607 287 607Q238 607 207.0 582.0Q176 557 176 510Q176 478 195.5 457.5Q215 437 245.0 425.0Q275 413 327 399Q396 380 439.5 361.0Q483 342 513.5 302.5Q544 263 544 197Q544 144 515.5 97.0Q487 50 432.5 21.5Q378 -7 304 -7Q234 -7 178.0 17.5Q122 42 90.0 87.0Q58 132 58 192Z"/>
<path transform="translate(73.17,29) scale(0.03,-0.03)" d="M208 458V153Q208 122 222.5 108.5Q237 95 272 95H342V0H252Q175 0 134.0 36.0Q93 72 93 153V458H28V551H93V688H208V551H342V458Z"/>
<path transform="translate(84.33,29) scale(0.03,-0.03)" d="M297 560Q362 560 410.5 534.5Q459 509 488 471V551H603V0H488V82Q459 43 409.0 17.0Q359 -9 295 -9Q224 -9 165.0 27.5Q106 64 71.5 129.5Q37 195 37 278Q37 361 71.5 425.0Q106 489 165.5 524.5Q225 560 297 560ZM321 461Q277 461 239.0 439.5Q201 418 177.5 376.5Q154 335 154 278Q154 221 177.5 178.0Q201 135 239.5 112.5Q278 90 321 90Q365 90 403.0 112.0Q441 134 464.5 176.5Q488 219 488 276Q488 333 464.5 375.0Q441 417 403.0 439.0Q365 461 321 461Z"/>
<path transform="translate(104.67,29) scale(0.03,-0.03)" d="M208 458V153Q208 122 222.5 108.5Q237 95 272 95H342V0H252Q175 0 134.0 36.0Q93 72 93 153V458H28V551H93V688H208V551H342V458Z"/>
<path transform="translate(115.83,29) scale(0.03,-0.03)" d="M45 169H163Q166 134 196.5 110.5Q227 87 273 87Q321 87 347.5 105.5Q374 124 374 153Q374 184 344.5 199.0Q315 214 251 232Q189 249 150.0 265.0Q111 281 82.5 314.0Q54 347 54 401Q54 445 80.0 481.5Q106 518 154.5 539.0Q203 560 266 560Q360 560 417.5 512.5Q475 465 479 383H365Q362 420 335.0 442.0Q308 464 262 464Q217 464 193.0 447.0Q169 430 169 402Q169 380 185.0 365.0Q201 350 224.0 341.5Q247 333 292 320Q352 304 390.5 287.5Q429 271 457.0 239.0Q485 207 486 154Q486 107 460.0 70.0Q434 33 386.5 12.0Q339 -9 275 -9Q210 -9 158.5 14.5Q107 38 77.0 78.5Q47 119 45 169Z"/>
</g>
<g fill="#8B949E">
<path transform="translate(131.85,29) scale(0.019,-0.019)" d="M48 66Q48 97 69.0 118.0Q90 139 121 139Q151 139 172.0 118.0Q193 97 193 66Q193 35 172.0 14.0Q151 -7 121 -7Q90 -7 69.0 14.0Q48 35 48 66Z"/>
<path transform="translate(136.429,29) scale(0.019,-0.019)" d="M60 697Q60 728 81.0 749.0Q102 770 133 770Q163 770 184.0 749.0Q205 728 205 697Q205 666 184.0 645.0Q163 624 133 624Q102 624 81.0 645.0Q60 666 60 697ZM189 551V0H75V551Z"/>
<path transform="translate(141.445,29) scale(0.019,-0.019)" d="M576 233H155Q160 167 204.0 127.0Q248 87 312 87Q404 87 442 164H565Q540 88 474.5 39.5Q409 -9 312 -9Q233 -9 170.5 26.5Q108 62 72.5 126.5Q37 191 37 276Q37 361 71.5 425.5Q106 490 168.5 525.0Q231 560 312 560Q390 560 451.0 526.0Q512 492 546.0 430.5Q580 369 580 289Q580 258 576 233ZM461 325Q460 388 416.0 426.0Q372 464 307 464Q248 464 206.0 426.5Q164 389 156 325Z"/>
</g>
</svg>'''

SHARED_STYLE = '''
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  background:#0f1419; color:#e8eaed; min-height:100vh; display:flex; flex-direction:column;
}
header {
  background:#161b22; border-bottom:1px solid #2a2f38; padding:20px 32px;
  display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
}
.logo svg { display:block; }
nav { display:flex; gap:24px; font-size:14px; }
nav a { color:#8b949e; text-decoration:none; transition:color .2s; }
nav a:hover { color:#fff; }
nav a.active-link { color:#fff; }
.header-divider { width:1px; height:24px; background:#2a2f38; margin:0 20px; }
.header-tagline { flex:1; color:#8b949e; font-size:14px; font-weight:500; }
main { flex:1; display:flex; flex-direction:column; align-items:center; padding:32px 16px; }
.breadcrumb { width:100%; max-width:1400px; font-size:13px; color:#6e7681; margin-bottom:14px; }
.breadcrumb a { color:#4f8cff; text-decoration:none; }
.breadcrumb a:hover { text-decoration:underline; }
.page-heading { width:100%; max-width:1400px; margin-bottom:24px; }
.page-heading h1 { font-size:22px; font-weight:600; color:#fff; margin-bottom:4px; }
.page-heading p { font-size:14px; color:#8b949e; max-width:760px; }
footer {
  display:grid; grid-template-columns:1fr 1fr 1fr; align-items:center; padding:22px 32px;
  text-align:center; color:#6e7681; font-size:13px; border-top:1px solid #2a2f38;
}
.footer-credit { text-align:center; }
.footer-email a { color:#6e7681; }
.footer-email a:hover { color:#8b949e; }
.social-links { display:flex; justify-content:center; gap:10px; }
.social-links a {
  display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px;
  border-radius:8px; background:#1c222c; border:1px solid #2a2f38; color:#8b949e;
  transition:color .2s,background .2s,border-color .2s;
}
.social-links a:hover { color:#fff; background:#242b36; border-color:#4f8cff; }
.social-links svg { width:17px; height:17px; }
@media (max-width:768px) { footer { grid-template-columns:1fr; gap:14px; text-align:center; } }
@media (max-width:640px) {
  header { padding:14px 16px; }
  .header-divider, .header-tagline { display:none; }
  nav { gap:16px; }
}

/* Insights index — post cards */
.insights-grid {
  width:100%; max-width:1400px; display:grid;
  grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:20px;
}
.post-card {
  background:#161b22; border:1px solid #2a2f38; border-radius:12px; overflow:hidden;
  text-decoration:none; color:inherit; display:flex; flex-direction:column;
  transition:border-color .2s,transform .15s;
}
.post-card:hover { border-color:#4f8cff; transform:translateY(-2px); }
.post-card-media { position:relative; width:100%; aspect-ratio:16/9; background:#0d1117; overflow:hidden; }
.post-card-media img { width:100%; height:100%; object-fit:cover; display:block; }
.post-card-media .play-badge {
  position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
}
.post-card-media .play-badge svg { width:44px; height:44px; opacity:.85; }
.post-card-body { padding:18px 20px 20px; display:flex; flex-direction:column; gap:8px; flex:1; }
.post-card-date { font-size:12px; color:#6e7681; }
.post-card-title { font-size:16px; font-weight:600; color:#fff; line-height:1.35; }
.post-card-desc { font-size:13px; color:#8b949e; line-height:1.5; flex:1; }
.post-card-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }
.post-tag {
  font-size:11px; font-weight:500; color:#8b949e; background:#1c222c;
  border:1px solid #2a2f38; border-radius:6px; padding:3px 8px;
}
.insights-empty { color:#6e7681; font-size:14px; }

/* Post page */
.post-wrapper { width:100%; max-width:900px; }
.post-video {
  width:100%; border-radius:12px; overflow:hidden; border:1px solid #2a2f38;
  background:#000; margin-bottom:28px; aspect-ratio:16/9;
}
.post-video video, .post-video iframe { width:100%; height:100%; display:block; border:0; }
.post-video.yt-facade { position:relative; cursor:pointer; }
.post-video.yt-facade img { width:100%; height:100%; object-fit:cover; display:block; }
.post-video.yt-facade .yt-play-badge {
  position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  transition:transform .15s;
}
.post-video.yt-facade:hover .yt-play-badge { transform:scale(1.06); }
.post-video.yt-vertical {
  aspect-ratio:9/16; max-width:380px; margin-left:auto; margin-right:auto;
}
.post-article { font-size:15px; line-height:1.7; color:#c9d1d9; }
.post-article h2 { font-size:18px; color:#fff; margin:28px 0 10px; }
.post-article p { margin-bottom:16px; }
.post-article ul { margin:0 0 16px 20px; }
.post-article li { margin-bottom:6px; }
.post-article a { color:#4f8cff; text-decoration:none; }
.post-article a:hover { text-decoration:underline; }
.post-meta-row {
  display:flex; align-items:center; gap:14px; margin-bottom:18px; flex-wrap:wrap;
}
.post-meta-row .post-card-date { font-size:13px; }
'''

COOKIE_BANNER_HTML = '''
<div id="cookie-banner" class="cookie-banner">
  <p>This site uses cookies to understand how visitors use it. No personal data is sold or shared with advertisers. <a href="#" id="cookie-learn-more">Learn more</a></p>
  <div class="cookie-actions">
    <button id="cookie-decline" class="cookie-btn cookie-btn-secondary">Decline</button>
    <button id="cookie-accept" class="cookie-btn cookie-btn-primary">Accept</button>
  </div>
</div>
<script>
(function() {
  const banner = document.getElementById('cookie-banner');
  const consent = localStorage.getItem('cookie_consent');
  if (!consent) banner.style.display = 'flex';
  document.getElementById('cookie-accept').addEventListener('click', function() {
    localStorage.setItem('cookie_consent', 'granted');
    if (typeof gtag === 'function') gtag('consent', 'update', { analytics_storage: 'granted' });
    banner.style.display = 'none';
  });
  document.getElementById('cookie-decline').addEventListener('click', function() {
    localStorage.setItem('cookie_consent', 'denied');
    banner.style.display = 'none';
  });
})();
</script>
'''

# Cookie banner CSS (unchanged from the rest of the site, duplicated here so
# this file is self-contained — merge with the shared stylesheet if one exists)
COOKIE_BANNER_CSS = '''
.cookie-banner {
  display:none; position:fixed; bottom:0; left:0; right:0; background:#161b22;
  border-top:1px solid #2a2f38; padding:16px 24px; z-index:1000; align-items:center;
  justify-content:space-between; gap:20px; flex-wrap:wrap; box-shadow:0 -4px 16px rgba(0,0,0,.3);
}
.cookie-banner p { color:#c9d1d9; font-size:13px; margin:0; max-width:640px; }
.cookie-banner a { color:#4f8cff; }
.cookie-actions { display:flex; gap:10px; flex-shrink:0; }
.cookie-btn { font-family:inherit; font-size:13px; font-weight:500; padding:9px 18px; border-radius:8px; cursor:pointer; border:1px solid #2a2f38; transition:background .2s; }
.cookie-btn-secondary { background:transparent; color:#8b949e; }
.cookie-btn-secondary:hover { background:#1c222c; }
.cookie-btn-primary { background:#4f8cff; color:#fff; border-color:#4f8cff; }
.cookie-btn-primary:hover { background:#3d7ae8; }
@media (max-width:640px) { .cookie-banner { flex-direction:column; align-items:stretch; } .cookie-actions { justify-content:flex-end; } }
'''

GA_SNIPPET = '''
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'analytics_storage': 'denied', 'ad_storage': 'denied',
    'ad_user_data': 'denied', 'ad_personalization': 'denied'
  });
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FDGVKJFFD3"></script>
<script>
  gtag('js', new Date());
  gtag('config', 'G-FDGVKJFFD3');
</script>
'''


def header_html(active="insights"):
    def cls(name):
        return ' class="active-link"' if name == active else ''
    return f'''<header>
  <div class="logo">
    <a href="/" aria-label="CarStats.ie — Home" style="display:block; line-height:0;">
    {LOGO_SVG}
    </a>
  </div>
  <div class="header-divider"></div>
  <div class="header-tagline">Irish Car Registration Statistics</div>
  <nav>
    <a href="/#dashboard"{cls('dashboard')}>Dashboard</a>
    <a href="/insights/"{cls('insights')}>Insights</a>
    <a href="/#about"{cls('about')}>About</a>
  </nav>
</header>'''


FOOTER_HTML = '''<footer id="about">
  <div class="footer-credit">
    Powered by <a href="https://www.linkedin.com/company/yes-analytics" target="_blank" rel="noopener">YeS Analytics</a> (<a href="https://www.linkedin.com/in/eugene-sierikov/" target="_blank" rel="noopener">Yevhen Sierikov</a>)
  </div>
  <div class="social-links">
    <a href="https://www.linkedin.com/company/yes-analytics" target="_blank" rel="noopener" aria-label="YeS Analytics on LinkedIn">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.38-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45z"/></svg>
    </a>
    <a href="https://x.com/CarStatsIE" target="_blank" rel="noopener" aria-label="CarStats.ie on X">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4.5 4.5l15 15M19.5 4.5l-15 15"/></svg>
    </a>
  </div>
  <div class="footer-email">
    <a href="mailto:info@carstats.ie">info@carstats.ie</a>
  </div>
</footer>'''


def page_shell(*, title, description, canonical, og_image, body, breadcrumb_jsonld="", extra_head=""):
    og_image_tag = f'https://carstats.ie{og_image}' if og_image else 'https://carstats.ie/site-assets/og_image.png'
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
{GA_SNIPPET}
<link rel="icon" type="image/svg+xml" href="/site-assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/site-assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/site-assets/favicon-16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/site-assets/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="/site-assets/favicon-192.png">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{og_image_tag}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og_image_tag}">
<link rel="canonical" href="{canonical}">
{breadcrumb_jsonld}
<style>
{SHARED_STYLE}
{COOKIE_BANNER_CSS}
</style>
{extra_head}
</head>
<body>
{body}
{COOKIE_BANNER_HTML}
</body>
</html>'''


def breadcrumb_jsonld(items):
    # items: list of (name, url)
    entries = ",\n".join(
        f'{{"@type":"ListItem","position":{i+1},"name":"{name}","item":"{url}"}}'
        for i, (name, url) in enumerate(items)
    )
    return f'''<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{entries}]}}
</script>'''


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def load_posts():
    posts = []
    if not os.path.isdir(CONTENT_DIR):
        return posts
    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(CONTENT_DIR, fname)
        post = frontmatter.load(fpath)
        meta = post.metadata
        required = ['title', 'slug', 'date', 'description']
        missing = [k for k in required if not meta.get(k)]
        if missing:
            print(f"  ⚠ Skipping {fname}: missing {missing}")
            continue
        meta['body_html'] = md.markdown(post.content, extensions=['extra'])
        meta['date_obj'] = datetime.strptime(str(meta['date']), '%Y-%m-%d')
        posts.append(meta)
    posts.sort(key=lambda p: p['date_obj'], reverse=True)
    return posts


def video_embed_html(meta):
    vtype = meta.get('video_type', 'file')
    src = meta.get('video_src', '')
    poster = meta.get('video_poster', '')
    if vtype == 'youtube':
        if 'shorts/' in src:
            vid = src.split('shorts/')[-1].split('?')[0].split('/')[0]
        elif 'youtube' in src or 'youtu.be' in src:
            vid = src.split('v=')[-1].split('/')[-1].split('&')[0]
        else:
            vid = src
        orientation = meta.get('video_orientation') or ('vertical' if 'shorts/' in src else 'horizontal')
        wrapper_class = 'post-video yt-facade' + (' yt-vertical' if orientation == 'vertical' else '')
        title_attr = meta['title'].replace('"', '&quot;')
        # Click-to-load facade: no YouTube request (and no cookie) until the
        # user actively presses play, consistent with the site's cookie
        # consent banner. Uses youtube-nocookie.com once loaded.
        poster_html = f'<img src="{poster}" alt="{title_attr}" loading="lazy">' if poster else ''
        return f'''<div class="{wrapper_class}" data-video-id="{vid}" data-title="{title_attr}" role="button" tabindex="0" aria-label="Play video: {title_attr}">
  {poster_html}
  <div class="yt-play-badge">
    <svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.5 7.7c-.8-2.9-2.5-5.2-5.4-6C55.8 0 34 0 34 0S12.2 0 6.9 1.7C4 2.5 2.3 4.8 1.5 7.7 0 13 0 24 0 24s0 11 1.5 16.3c.8 2.9 2.5 5.2 5.4 6C12.2 48 34 48 34 48s21.8 0 27.1-1.7c2.9-.8 4.6-3.1 5.4-6C68 35 68 24 68 24s0-11-1.5-16.3z" fill="rgba(15,20,25,.75)"/><path d="M45 24 27 14v20z" fill="#fff"/></svg>
  </div>
</div>
<script>
(function() {{
  document.querySelectorAll('.yt-facade').forEach(function(el) {{
    function load() {{
      var vid = el.getAttribute('data-video-id');
      var title = el.getAttribute('data-title');
      el.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + vid + '?autoplay=1" title="' + title + '" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>';
    }}
    el.addEventListener('click', load);
    el.addEventListener('keydown', function(e) {{ if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); load(); }} }});
  }});
}})();
</script>'''
    poster_attr = f' poster="{poster}"' if poster else ''
    return f'<div class="post-video"><video controls preload="metadata"{poster_attr}><source src="{src}" type="video/mp4"></video></div>'


def render_post_page(meta):
    canonical = f'{SITE_ROOT}/insights/{meta["slug"]}/'
    date_str = meta['date_obj'].strftime('%d %B %Y')
    tags = meta.get('tags') or []
    tags_html = ''.join(f'<span class="post-tag">{t}</span>' for t in tags)

    bc_json = breadcrumb_jsonld([
        ("Home", SITE_ROOT + "/"),
        ("Insights", SITE_ROOT + "/insights/"),
        (meta['title'], canonical),
    ])

    body = f'''{header_html(active="insights")}
<main>
  <div class="breadcrumb"><a href="/">Home</a> / <a href="/insights/">Insights</a> / {meta['title']}</div>
  <div class="post-wrapper">
    <div class="page-heading">
      <h1>{meta['title']}</h1>
    </div>
    <div class="post-meta-row">
      <span class="post-card-date">{date_str}</span>
      <div class="post-card-tags">{tags_html}</div>
    </div>
    {video_embed_html(meta)}
    <div class="post-article">
{meta['body_html']}
    </div>
  </div>
</main>
{FOOTER_HTML}'''

    return page_shell(
        title=f"{meta['title']} — CarStats.ie Insights",
        description=meta['description'],
        canonical=canonical,
        og_image=meta.get('og_image') or meta.get('video_poster'),
        body=body,
        breadcrumb_jsonld=bc_json,
    )


def render_index_page(posts):
    canonical = f'{SITE_ROOT}/insights/'
    bc_json = breadcrumb_jsonld([
        ("Home", SITE_ROOT + "/"),
        ("Insights", canonical),
    ])

    if posts:
        cards = []
        for p in posts:
            date_str = p['date_obj'].strftime('%d %B %Y')
            tags_html = ''.join(f'<span class="post-tag">{t}</span>' for t in (p.get('tags') or []))
            poster = p.get('video_poster', '')
            media = f'<img src="{poster}" alt="{p["title"]}" loading="lazy">' if poster else ''
            cards.append(f'''<a class="post-card" href="/insights/{p['slug']}/">
      <div class="post-card-media">
        {media}
        <div class="play-badge">
          <svg viewBox="0 0 24 24" fill="#ffffff"><circle cx="12" cy="12" r="11" fill="rgba(15,20,25,0.55)"/><path d="M10 8l6 4-6 4V8z"/></svg>
        </div>
      </div>
      <div class="post-card-body">
        <span class="post-card-date">{date_str}</span>
        <span class="post-card-title">{p['title']}</span>
        <span class="post-card-desc">{p['description']}</span>
        <div class="post-card-tags">{tags_html}</div>
      </div>
    </a>''')
        grid = f'<div class="insights-grid">\n' + '\n'.join(cards) + '\n</div>'
    else:
        grid = '<p class="insights-empty">No posts yet. Check back soon.</p>'

    body = f'''{header_html(active="insights")}
<main>
  <div class="breadcrumb"><a href="/">Home</a> / Insights</div>
  <div class="page-heading">
    <h1>Insights</h1>
    <p>Commentary, visualizations, and short write-ups built on top of the CarStats.ie dataset.</p>
  </div>
  {grid}
</main>
{FOOTER_HTML}'''

    return page_shell(
        title="Insights — CarStats.ie",
        description="Commentary, visualizations, and short write-ups on Irish car registration trends, built on the CarStats.ie dataset.",
        canonical=canonical,
        og_image="/site-assets/og_image.png",
        body=body,
        breadcrumb_jsonld=bc_json,
    )


def main():
    posts = load_posts()
    print(f"Loaded {len(posts)} post(s)")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_index_page(posts))
    print("  ✓ Wrote insights/index.html")

    for p in posts:
        post_dir = os.path.join(OUTPUT_DIR, p['slug'])
        os.makedirs(post_dir, exist_ok=True)
        with open(os.path.join(post_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(render_post_page(p))
        print(f"  ✓ Wrote insights/{p['slug']}/index.html")


if __name__ == '__main__':
    main()
