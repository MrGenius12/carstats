"""
Fix the Facebook link: it was mistakenly set to a personal profile URL
instead of the actual CarStats.ie Facebook Page. Replaces the old ID with
the correct one wherever it appears. Safe to run more than once.

Usage:
    cd path/to/carstats-repo
    python fix_facebook_link.py
"""

import os

OLD_URL = "https://www.facebook.com/profile.php?id=61592773460087"
NEW_URL = "https://www.facebook.com/profile.php?id=61592304374036"


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    changed, skipped = [], []

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            if OLD_URL not in content:
                skipped.append(fpath)
                continue

            content = content.replace(OLD_URL, NEW_URL)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            changed.append(fpath)

    print(f"Updated {len(changed)} file(s):")
    for f in changed:
        print(f"  ✓ {os.path.relpath(f, root)}")

    if skipped:
        print(f"\nNo old link found, left as-is ({len(skipped)}):")
        for f in skipped:
            print(f"  - {os.path.relpath(f, root)}")


if __name__ == '__main__':
    main()
