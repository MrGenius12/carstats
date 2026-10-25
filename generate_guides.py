"""
CarStats.ie | Guides generator

Builds the /guides/ section from Markdown files:
  - /guides/                 index page (list of all guides)
  - /guides/<slug>/          one page per guide

Shares header, footer, nav, cookie banner, GA and base styles with
generate_insights.py, so any change to the site chrome is made once there.

Usage:
    pip install python-frontmatter markdown
    python generate_guides.py
    python update_sitemap.py

Content:
    Add a .md file to content/guides/ for each guide. Frontmatter fields:

    title        (required) page <title> / <h1>
    slug         (required) URL segment -> /guides/<slug>/
    date         (required) YYYY-MM-DD, shown on cards and the guide page
    description  (required) meta description / og:description / card text
    tags         optional list of short tags shown on the card
    og_image     optional og:image (defaults to the site image)

    Body is Markdown (tables, headings, lists supported).
"""

import os
from datetime import datetime

import frontmatter
import markdown as md

from generate_insights import (
    SITE_ROOT,
    FOOTER_HTML,
    header_html,
    page_shell,
    breadcrumb_jsonld,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content", "guides")
OUTPUT_DIR = os.path.join(BASE_DIR, "guides")

GUIDES_CSS = '''<style>
.guides-list {
  width:100%; max-width:1400px; display:grid;
  grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr)); gap:20px;
}
.guide-card {
  background:#161b22; border:1px solid #2a2f38; border-radius:12px; padding:20px 22px;
  text-decoration:none; color:inherit; display:flex; flex-direction:column; gap:8px;
  transition:border-color .2s,transform .15s;
}
.guide-card:hover { border-color:#4f8cff; transform:translateY(-2px); }
.guide-card-label { font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:#4f8cff; }
.guide-card-title { font-size:17px; font-weight:600; color:#fff; line-height:1.35; }
.guide-card-desc { font-size:13px; color:#8b949e; line-height:1.55; flex:1; }
.guide-card-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }
.guide-tag {
  font-size:11px; font-weight:500; color:#8b949e; background:#1c222c;
  border:1px solid #2a2f38; border-radius:6px; padding:3px 8px;
}
.guide-wrapper { width:100%; max-width:900px; }
.guide-intro { font-size:15px; color:#8b949e; margin-top:6px; }
.post-article h3 { font-size:16px; color:#fff; margin:22px 0 8px; }
.post-article strong { color:#fff; }
.post-article code {
  font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace; font-size:13px;
  background:#1c222c; border:1px solid #2a2f38; border-radius:5px; padding:1px 6px; color:#e8eaed;
}
.post-article hr { border:0; border-top:1px solid #2a2f38; margin:28px 0; }
.post-article em { color:#8b949e; }
.post-article .table-scroll { width:100%; overflow-x:auto; margin:0 0 20px; }
.post-article table {
  width:100%; border-collapse:collapse; font-size:14px; background:#161b22;
  border:1px solid #2a2f38; border-radius:10px; overflow:hidden;
}
.post-article th, .post-article td { padding:10px 14px; text-align:left; border-bottom:1px solid #2a2f38; vertical-align:top; }
.post-article th { color:#8b949e; font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; background:#1c222c; }
.post-article tr:last-child td { border-bottom:0; }
@media (max-width:640px) { .post-article th, .post-article td { padding:8px 10px; } }
</style>'''


def load_guides():
    guides = []
    if not os.path.isdir(CONTENT_DIR):
        return guides
    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        post = frontmatter.load(os.path.join(CONTENT_DIR, fname))
        meta = post.metadata
        missing = [k for k in ('title', 'slug', 'date', 'description') if not meta.get(k)]
        if missing:
            print(f"  ! Skipping {fname}: missing {missing}")
            continue
        html = md.markdown(post.content, extensions=['extra'])
        # Wrap tables so they scroll horizontally on narrow screens
        html = html.replace('<table>', '<div class="table-scroll"><table>').replace('</table>', '</table></div>')
        meta['body_html'] = html
        meta['date_obj'] = datetime.strptime(str(meta['date']), '%Y-%m-%d')
        guides.append(meta)
    guides.sort(key=lambda g: g['date_obj'], reverse=True)
    return guides


def render_guide_page(meta):
    canonical = f'{SITE_ROOT}/guides/{meta["slug"]}/'
    date_str = meta['date_obj'].strftime('%d %B %Y')
    bc_json = breadcrumb_jsonld([
        ("Home", SITE_ROOT + "/"),
        ("Guides", SITE_ROOT + "/guides/"),
        (meta['title'], canonical),
    ])
    article_json = f'''<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{meta['title']}","description":"{meta['description']}","datePublished":"{meta['date_obj'].strftime('%Y-%m-%d')}","author":{{"@type":"Organization","name":"YeS Analytics"}},"publisher":{{"@type":"Organization","name":"CarStats.ie"}},"mainEntityOfPage":"{canonical}"}}
</script>'''

    body = f'''{header_html(active="guides")}
<main>
  <div class="breadcrumb"><a href="/">Home</a> / <a href="/guides/">Guides</a> / {meta['title']}</div>
  <div class="guide-wrapper">
    <div class="page-heading">
      <h1>{meta['title']}</h1>
    </div>
    <div class="post-meta-row">
      <span class="post-card-date">Last updated {date_str}</span>
    </div>
    <div class="post-article">
{meta['body_html']}
    </div>
  </div>
</main>
{FOOTER_HTML}'''

    return page_shell(
        title=f"{meta['title']} | CarStats.ie Guides",
        description=meta['description'],
        canonical=canonical,
        og_image=meta.get('og_image') or '/site-assets/og_image.png',
        body=body,
        breadcrumb_jsonld=bc_json + '\n' + article_json,
        extra_head=GUIDES_CSS,
    )


def render_index_page(guides):
    canonical = f'{SITE_ROOT}/guides/'
    bc_json = breadcrumb_jsonld([
        ("Home", SITE_ROOT + "/"),
        ("Guides", canonical),
    ])

    if guides:
        cards = []
        for g in guides:
            tags = ''.join(f'<span class="guide-tag">{t}</span>' for t in (g.get('tags') or []))
            tags_html = f'<div class="guide-card-tags">{tags}</div>' if tags else ''
            cards.append(f'''<a class="guide-card" href="/guides/{g['slug']}/">
      <span class="guide-card-label">Guide</span>
      <span class="guide-card-title">{g['title']}</span>
      <span class="guide-card-desc">{g['description']}</span>
      {tags_html}
    </a>''')
        grid = '<div class="guides-list">\n' + '\n'.join(cards) + '\n</div>'
    else:
        grid = '<p class="insights-empty">No guides yet. Check back soon.</p>'

    body = f'''{header_html(active="guides")}
<main>
  <div class="breadcrumb"><a href="/">Home</a> / Guides</div>
  <div class="page-heading">
    <h1>Guides</h1>
    <p>Plain-English explainers on buying, registering and owning a car in Ireland, checked against official sources.</p>
  </div>
  {grid}
</main>
{FOOTER_HTML}'''

    return page_shell(
        title="Guides | CarStats.ie",
        description="Plain-English guides to buying, registering and owning a car in Ireland, checked against official sources such as Revenue.",
        canonical=canonical,
        og_image="/site-assets/og_image.png",
        body=body,
        breadcrumb_jsonld=bc_json,
        extra_head=GUIDES_CSS,
    )


def main():
    guides = load_guides()
    print(f"Loaded {len(guides)} guide(s)")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_index_page(guides))
    print("  + Wrote guides/index.html")
    for g in guides:
        out_dir = os.path.join(OUTPUT_DIR, g['slug'])
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(render_guide_page(g))
        print(f"  + Wrote guides/{g['slug']}/index.html")


if __name__ == '__main__':
    main()
