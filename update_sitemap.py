"""
CarStats.ie | Sitemap builder

Rebuilds sitemap.xml from every folder in the repo that contains an
index.html, so new dashboards, Insights posts and Guides are never left
out. Run it after generate_insights.py / generate_guides.py, or after
adding any new page.

Usage:
    python update_sitemap.py
"""

import os
from xml.sax.saxutils import escape

SITE_ROOT = "https://carstats.ie"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folders that are never pages
SKIP_DIRS = {'.git', '.github', 'content', 'site-assets', 'media', '__pycache__', 'node_modules'}

# Section rules: (path prefix, changefreq, priority). First match wins.
SECTION_RULES = [
    ('/insights/', 'weekly', '0.8', True),   # exact index only
    ('/guides/', 'monthly', '0.7', True),
    ('/insights/', 'monthly', '0.6', False),  # individual posts
    ('/guides/', 'monthly', '0.6', False),
    ('/privacy/', 'yearly', '0.3', True),
    ('/buying-tools/', 'monthly', '0.7', True),
    ('/car-check-comparison/', 'monthly', '0.7', True),
    ('/where-to-buy-a-car/', 'monthly', '0.7', True),
]
DEFAULT = ('monthly', '0.8')   # dashboard pages


def find_pages():
    pages = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
        if 'index.html' not in files:
            continue
        rel = os.path.relpath(root, BASE_DIR).replace(os.sep, '/')
        path = '/' if rel == '.' else f'/{rel}/'
        pages.append(path)
    return pages


def rules_for(path):
    if path == '/':
        return 'monthly', '1.0'
    for prefix, freq, prio, exact in SECTION_RULES:
        if (exact and path == prefix) or (not exact and path.startswith(prefix) and path != prefix):
            return freq, prio
    return DEFAULT


def sort_key(path):
    order = ['/', '/insights/', '/guides/']
    if path in order:
        return (0, order.index(path), path)
    if path.startswith('/insights/'):
        return (2, 0, path)
    if path.startswith('/guides/'):
        return (3, 0, path)
    return (1, 0, path)


def main():
    pages = sorted(find_pages(), key=sort_key)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        freq, prio = rules_for(p)
        lines += ['  <url>',
                  f'    <loc>{escape(SITE_ROOT + p)}</loc>',
                  f'    <changefreq>{freq}</changefreq>',
                  f'    <priority>{prio}</priority>',
                  '  </url>']
    lines.append('</urlset>')
    with open(os.path.join(BASE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Wrote sitemap.xml with {len(pages)} URLs")


if __name__ == '__main__':
    main()
