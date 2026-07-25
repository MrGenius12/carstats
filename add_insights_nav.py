"""
Insert the "Insights" nav link into every page of the carstats.ie site.

Finds this exact block (present identically in all 16 pages):

    <a href="/#dashboard">Dashboard</a>
    <a href="/#about">About</a>

and turns it into:

    <a href="/#dashboard">Dashboard</a>
    <a href="/insights/">Insights</a>
    <a href="/#about">About</a>

Safe to run more than once: files that already have the Insights link are
left untouched and reported as "already has it".

Usage:
    cd path/to/carstats-repo
    python add_insights_nav.py
"""

import os

OLD_BLOCK = '''<a href="/#dashboard">Dashboard</a>
    <a href="/#about">About</a>'''

NEW_BLOCK = '''<a href="/#dashboard">Dashboard</a>
    <a href="/insights/">Insights</a>
    <a href="/#about">About</a>'''


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    changed, already, skipped = [], [], []

    for dirpath, _, filenames in os.walk(root):
        # Don't touch the insights section itself, or anything outside html files
        if os.sep + 'insights' + os.sep in dirpath + os.sep:
            continue
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'href="/insights/"' in content:
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
        print(f"\nAlready had the Insights link ({len(already)}):")
        for f in already:
            print(f"  - {os.path.relpath(f, root)}")

    if skipped:
        print(f"\n⚠ Nav block not found, check manually ({len(skipped)}):")
        for f in skipped:
            print(f"  ! {os.path.relpath(f, root)}")


if __name__ == '__main__':
    main()
