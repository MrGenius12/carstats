"""
Ensure ALL social icons (YouTube, TikTok, Instagram, Threads, Facebook) are
present in the footer, independently of each other. Each icon is checked on
its own -- if it's missing, it gets added; if it's already there, that page
is left alone for that icon. This avoids the fragile "must match this exact
previous block" chaining that caused earlier one-shot scripts to silently
skip real files.

Anchors on the boundary between .social-links and .footer-email, which
exists on every page regardless of how many icons are currently inside
.social-links.

Safe to run more than once, and safe to run even if some icons already
exist and others don't.

Usage:
    cd path/to/carstats-repo
    python ensure_all_social_icons.py
"""

import os

BOUNDARY = '''  </div>
  <div class="footer-email">'''

ICONS = [
    {
        "marker": "CarStats.ie on YouTube",
        "html": '''  <a href="https://www.youtube.com/@CarStatsIE" target="_blank" rel="noopener" aria-label="CarStats.ie on YouTube">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.6 15.5V8.5l6.3 3.5-6.3 3.5z"/></svg>
    </a>
''',
    },
    {
        "marker": "CarStats.ie on TikTok",
        "html": '''  <a href="https://www.tiktok.com/@carstats.ie" target="_blank" rel="noopener" aria-label="CarStats.ie on TikTok">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.6 5.82c-.9-.83-1.47-2-1.66-3.32h-3.02v14.1c0 1.4-1.14 2.53-2.53 2.53a2.53 2.53 0 0 1-2.53-2.53 2.53 2.53 0 0 1 2.53-2.53c.26 0 .5.04.74.1V11.1a5.6 5.6 0 0 0-.74-.05A5.58 5.58 0 0 0 4.06 16.6 5.58 5.58 0 0 0 9.64 22.2a5.58 5.58 0 0 0 5.58-5.58V9.35a8.16 8.16 0 0 0 4.76 1.52V7.85a4.85 4.85 0 0 1-3.38-2.03z"/></svg>
    </a>
''',
    },
    {
        "marker": "CarStats.ie on Instagram",
        "html": '''  <a href="https://www.instagram.com/carstats.ie/" target="_blank" rel="noopener" aria-label="CarStats.ie on Instagram">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.8.24 2.22.4.56.21.96.47 1.38.89.42.42.68.82.89 1.38.16.42.35 1.05.4 2.22.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.24 1.8-.4 2.22-.21.56-.47.96-.89 1.38-.42.42-.82.68-1.38.89-.42.16-1.05.35-2.22.4-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.24-2.22-.4a3.72 3.72 0 0 1-1.38-.89 3.72 3.72 0 0 1-.89-1.38c-.16-.42-.35-1.05-.4-2.22-.06-1.27-.07-1.65-.07-4.85s.01-3.58.07-4.85c.05-1.17.24-1.8.4-2.22.21-.56.47-.96.89-1.38.42-.42.82-.68 1.38-.89.42-.16 1.05-.35 2.22-.4C8.42 2.17 8.8 2.16 12 2.16zm0 1.62c-3.15 0-3.5.01-4.73.07-1.03.05-1.6.22-1.97.36-.5.19-.85.42-1.22.79-.37.37-.6.72-.79 1.22-.14.37-.31.94-.36 1.97-.06 1.23-.07 1.58-.07 4.73s.01 3.5.07 4.73c.05 1.03.22 1.6.36 1.97.19.5.42.85.79 1.22.37.37.72.6 1.22.79.37.14.94.31 1.97.36 1.23.06 1.58.07 4.73.07s3.5-.01 4.73-.07c1.03-.05 1.6-.22 1.97-.36.5-.19.85-.42 1.22-.79.37-.37.6-.72.79-1.22.14-.37.31-.94.36-1.97.06-1.23.07-1.58.07-4.73s-.01-3.5-.07-4.73c-.05-1.03-.22-1.6-.36-1.97a3.28 3.28 0 0 0-.79-1.22 3.28 3.28 0 0 0-1.22-.79c-.37-.14-.94-.31-1.97-.36-1.23-.06-1.58-.07-4.73-.07zm0 4.14a5.08 5.08 0 1 1 0 10.16 5.08 5.08 0 0 1 0-10.16zm0 1.62a3.46 3.46 0 1 0 0 6.92 3.46 3.46 0 0 0 0-6.92zm5.29-1.8a1.19 1.19 0 1 1-2.38 0 1.19 1.19 0 0 1 2.38 0z"/></svg>
    </a>
''',
    },
    {
        "marker": "CarStats.ie on Threads",
        "html": '''  <a href="https://www.threads.com/@carstats.ie/" target="_blank" rel="noopener" aria-label="CarStats.ie on Threads">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12.2 22c-2.85 0-5.1-.83-6.68-2.46C3.9 17.85 3.1 15.4 3.08 12.05v-.03c.02-3.3.82-5.75 2.44-7.44C7.1 2.85 9.35 2 12.2 2c2.7 0 4.85.75 6.4 2.24 1.4 1.34 2.24 3.16 2.5 5.4l-1.98.22c-.22-1.84-.87-3.28-1.98-4.33-1.18-1.13-2.87-1.71-5.02-1.71-2.3 0-4.08.68-5.3 2.03-1.2 1.33-1.83 3.3-1.85 5.87.02 2.5.65 4.42 1.85 5.75 1.2 1.33 2.9 2.02 5.06 2.05.4 0 .78-.02 1.14-.08a4.9 4.9 0 0 1-1.83-2.63c-.32-1.16-.24-2.44.33-3.44.6-1.07 1.7-1.83 3.13-2.13a8.9 8.9 0 0 1 3.28-.06 4.7 4.7 0 0 0-.9-1.72c-.6-.68-1.5-1.05-2.7-1.08-1.36-.04-2.55.35-3.55 1.15l-1.14-1.6c1.34-1.06 2.94-1.6 4.75-1.55 1.8.04 3.24.63 4.28 1.75 1 1.07 1.55 2.5 1.63 4.25.02.28.02.55.02.83 0 2.5-.7 4.5-2.05 5.94-1.5 1.6-3.7 2.44-6.4 2.44zm.32-9.9c-.24 0-.47.01-.7.04-.9.13-1.55.5-1.87 1.08-.28.5-.32 1.14-.13 1.8.25.9.98 1.55 2.03 1.83.87.23 1.83.16 2.7-.2 1.03-.42 1.75-1.28 2.02-2.42.12-.53.13-1.06.04-1.56a7.13 7.13 0 0 0-2.53-.5c-.5-.04-1.02-.06-1.56-.07z"/></svg>
    </a>
''',
    },
    {
        "marker": "CarStats.ie on Facebook",
        "html": '''  <a href="https://www.facebook.com/profile.php?id=61592304374036" target="_blank" rel="noopener" aria-label="CarStats.ie on Facebook">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12.06C22 6.51 17.52 2 12 2S2 6.51 2 12.06c0 5 3.66 9.15 8.44 9.94v-7.03H7.9v-2.91h2.54V9.85c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56v1.89h2.78l-.44 2.91h-2.34V22c4.78-.79 8.44-4.94 8.44-9.94z"/></svg>
    </a>
''',
    },
]


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    report = {icon["marker"]: {"added": [], "already": []} for icon in ICONS}
    boundary_missing = []

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            if BOUNDARY not in content:
                boundary_missing.append(fpath)
                continue

            changed = False
            for icon in ICONS:
                if icon["marker"] in content:
                    report[icon["marker"]]["already"].append(fpath)
                    continue
                content = content.replace(BOUNDARY, icon["html"] + BOUNDARY)
                report[icon["marker"]]["added"].append(fpath)
                changed = True

            if changed:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)

    root_rel = lambda f: os.path.relpath(f, root)

    for marker, data in report.items():
        print(f"\n{marker}")
        print(f"  Added: {len(data['added'])}")
        for f in data["added"]:
            print(f"    ✓ {root_rel(f)}")
        if data["already"]:
            print(f"  Already had it: {len(data['already'])}")

    if boundary_missing:
        print(f"\n⚠ Footer boundary not found, check manually ({len(boundary_missing)}):")
        for f in boundary_missing:
            print(f"  ! {root_rel(f)}")


if __name__ == '__main__':
    main()
