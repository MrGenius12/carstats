"""
Ensure the Facebook icon is present in the footer with the correct Page
link, regardless of what other social icons (Instagram/Threads/TikTok)
already made it onto a given page. Anchors on the boundary between
.social-links and .footer-email, which exists on every page regardless of
how many icons are currently inside .social-links.

- If the Facebook icon is missing entirely: adds it.
- If it's present with the old (wrong, personal-profile) link: fixes the URL.
- If it's already correct: leaves the file alone.

Safe to run more than once.

Usage:
    cd path/to/carstats-repo
    python ensure_facebook_icon.py
"""

import os

OLD_FB_URL = "https://www.facebook.com/profile.php?id=61592773460087"
CORRECT_FB_URL = "https://www.facebook.com/profile.php?id=61592304374036"

BOUNDARY = '''  </div>
  <div class="footer-email">'''

FACEBOOK_LINK = '''  <a href="''' + CORRECT_FB_URL + '''" target="_blank" rel="noopener" aria-label="CarStats.ie on Facebook">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12.06C22 6.51 17.52 2 12 2S2 6.51 2 12.06c0 5 3.66 9.15 8.44 9.94v-7.03H7.9v-2.91h2.54V9.85c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56v1.89h2.78l-.44 2.91h-2.34V22c4.78-.79 8.44-4.94 8.44-9.94z"/></svg>
    </a>
'''


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    added, fixed, already_ok, skipped = [], [], [], []

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            original = content

            if OLD_FB_URL in content:
                content = content.replace(OLD_FB_URL, CORRECT_FB_URL)
                fixed.append(fpath)
            elif CORRECT_FB_URL in content:
                already_ok.append(fpath)
            elif BOUNDARY in content:
                content = content.replace(BOUNDARY, FACEBOOK_LINK + BOUNDARY)
                added.append(fpath)
            else:
                skipped.append(fpath)
                continue

            if content != original:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)

    print(f"Added Facebook icon ({len(added)}):")
    for f in added:
        print(f"  ✓ {os.path.relpath(f, root)}")

    print(f"\nFixed wrong link ({len(fixed)}):")
    for f in fixed:
        print(f"  ✓ {os.path.relpath(f, root)}")

    if already_ok:
        print(f"\nAlready correct ({len(already_ok)}):")
        for f in already_ok:
            print(f"  - {os.path.relpath(f, root)}")

    if skipped:
        print(f"\n⚠ Boundary not found, check manually ({len(skipped)}):")
        for f in skipped:
            print(f"  ! {os.path.relpath(f, root)}")


if __name__ == '__main__':
    main()
