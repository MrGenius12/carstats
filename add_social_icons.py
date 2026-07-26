"""
Add YouTube and TikTok icons to the footer social-links row, next to the
existing LinkedIn and X icons.

Finds the exact X (Twitter) icon block (present identically in all pages)
and inserts the two new icons right after it, before the closing </div>.
Safe to run more than once.

Usage:
    cd path/to/carstats-repo
    python add_social_icons.py
"""

import os

OLD_BLOCK = '''<a href="https://x.com/CarStatsIE" target="_blank" rel="noopener" aria-label="CarStats.ie on X">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4.5 4.5l15 15M19.5 4.5l-15 15"/></svg>
    </a>
  </div>'''

NEW_BLOCK = '''<a href="https://x.com/CarStatsIE" target="_blank" rel="noopener" aria-label="CarStats.ie on X">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4.5 4.5l15 15M19.5 4.5l-15 15"/></svg>
    </a>
    <a href="https://www.youtube.com/@CarStatsIE" target="_blank" rel="noopener" aria-label="CarStats.ie on YouTube">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.6 15.5V8.5l6.3 3.5-6.3 3.5z"/></svg>
    </a>
    <a href="https://www.tiktok.com/@carstats.ie" target="_blank" rel="noopener" aria-label="CarStats.ie on TikTok">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.6 5.82c-.9-.83-1.47-2-1.66-3.32h-3.02v14.1c0 1.4-1.14 2.53-2.53 2.53a2.53 2.53 0 0 1-2.53-2.53 2.53 2.53 0 0 1 2.53-2.53c.26 0 .5.04.74.1V11.1a5.6 5.6 0 0 0-.74-.05A5.58 5.58 0 0 0 4.06 16.6 5.58 5.58 0 0 0 9.64 22.2a5.58 5.58 0 0 0 5.58-5.58V9.35a8.16 8.16 0 0 0 4.76 1.52V7.85a4.85 4.85 0 0 1-3.38-2.03z"/></svg>
    </a>
  </div>'''


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    changed, already, skipped = [], [], []

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'CarStats.ie on YouTube' in content:
                already.append(fpath)
                continue
            if OLD_BLOCK not in content:
                skipped.append(fpath)
                continue

            content = content.replace(OLD_BLOCK, NEW_BLOCK)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            changed.append(fpath)

    print(f"Updated {len(changed)} file(s):")
    for f in changed:
        print(f"  ✓ {os.path.relpath(f, root)}")

    if already:
        print(f"\nAlready had the icons ({len(already)}):")
        for f in already:
            print(f"  - {os.path.relpath(f, root)}")

    if skipped:
        print(f"\n⚠ Block not found, check manually ({len(skipped)}):")
        for f in skipped:
            print(f"  ! {os.path.relpath(f, root)}")


if __name__ == '__main__':
    main()
