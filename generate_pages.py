"""
CarStats.ie | Standalone pages generator

Builds simple standalone pages that share the site chrome:
  - /<slug>/      one page per Markdown file in content/pages/ (e.g. /privacy/)
  - /404.html     custom "page not found" page served by GitHub Pages

Uses the shared header, footer, styles and article CSS from
generate_insights.py and generate_guides.py.

Usage:
    python generate_pages.py
    python update_sitemap.py

Content (content/pages/*.md) frontmatter:
    title        (required) page <title> / <h1>
    slug         (required) URL segment -> /<slug>/
    date         (required) YYYY-MM-DD, shown as "Last updated"
    description  (required) meta description
"""

import os
from datetime import datetime

import frontmatter
import markdown as md

from generate_insights import SITE_ROOT, FOOTER_HTML, header_html, page_shell, breadcrumb_jsonld
from generate_guides import GUIDES_CSS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, "content", "pages")

NOT_FOUND_CSS = '''<style>
.nf-wrapper { width:100%; max-width:640px; text-align:center; padding:48px 0 24px; }
.nf-code { font-size:64px; font-weight:700; color:#4f8cff; line-height:1; margin-bottom:12px; }
.nf-wrapper h1 { font-size:22px; color:#fff; margin-bottom:10px; }
.nf-wrapper p { font-size:15px; color:#8b949e; line-height:1.6; margin-bottom:28px; }
.nf-links { display:flex; flex-wrap:wrap; justify-content:center; gap:10px; }
.nf-links a {
  font-size:14px; font-weight:500; text-decoration:none; padding:10px 18px; border-radius:8px;
  border:1px solid #2a2f38; background:#161b22; color:#c9d1d9; transition:border-color .2s,color .2s;
}
.nf-links a:hover { border-color:#4f8cff; color:#fff; }
.nf-links a.primary { background:#4f8cff; border-color:#4f8cff; color:#fff; }
.nf-links a.primary:hover { background:#3d7ae8; }
</style>
<meta name="robots" content="noindex">'''


def load_pages():
    pages = []
    if not os.path.isdir(CONTENT_DIR):
        return pages
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
        html = html.replace('<table>', '<div class="table-scroll"><table>').replace('</table>', '</table></div>')
        meta['body_html'] = html
        meta['date_obj'] = datetime.strptime(str(meta['date']), '%Y-%m-%d')
        pages.append(meta)
    return pages


def render_page(meta):
    canonical = f'{SITE_ROOT}/{meta["slug"]}/'
    date_str = meta['date_obj'].strftime('%d %B %Y')
    body = f'''{header_html(active=meta["slug"])}
<main>
  <div class="breadcrumb"><a href="/">Home</a> / {meta['title']}</div>
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
        title=f"{meta['title']} | CarStats.ie",
        description=meta['description'],
        canonical=canonical,
        og_image='/site-assets/og_image.png',
        body=body,
        breadcrumb_jsonld=breadcrumb_jsonld([("Home", SITE_ROOT + "/"), (meta['title'], canonical)]),
        extra_head=GUIDES_CSS,
    )


def render_404():
    body = f'''{header_html(active="")}
<main>
  <div class="nf-wrapper">
    <div class="nf-code">404</div>
    <h1>Page not found</h1>
    <p>The page may have moved, or the address may contain a typo. The dashboards, Insights and Guides are all still available from the links below.</p>
    <div class="nf-links">
      <a class="primary" href="/">Go to the dashboard</a>
      <a href="/insights/">Insights</a>
      <a href="/guides/">Guides</a>
      <a href="/buying-tools/">Buying Tools</a>
    </div>
  </div>
</main>
{FOOTER_HTML}'''
    return page_shell(
        title="Page not found | CarStats.ie",
        description="The requested page could not be found on CarStats.ie.",
        canonical=SITE_ROOT + "/",
        og_image='/site-assets/og_image.png',
        body=body,
        extra_head=NOT_FOUND_CSS,
    )


def main():
    pages = load_pages()
    print(f"Loaded {len(pages)} page(s)")
    for p in pages:
        out_dir = os.path.join(BASE_DIR, p['slug'])
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(render_page(p))
        print(f"  + Wrote {p['slug']}/index.html")
    with open(os.path.join(BASE_DIR, '404.html'), 'w', encoding='utf-8') as f:
        f.write(render_404())
    print("  + Wrote 404.html")


if __name__ == '__main__':
    main()
