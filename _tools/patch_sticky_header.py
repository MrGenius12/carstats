"""Make the site header sticky on desktop only (min-width 641px).

Mobile (<= 640px) is left untouched. Idempotent: skips files that
already contain the /* sticky-header */ marker.

Patches every HTML page that has the /* nav-wrap */ CSS line, plus the
NAV_DD_CSS template in generate_insights.py (shared by all generators).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = '/* sticky-header */'
ANCHOR = '/* nav-wrap */'
RULE = ('/* sticky-header */ @media (min-width: 641px) { '
        'header { position: sticky; top: 0; z-index: 100; } '
        'html { scroll-padding-top: 96px; } }\n  ')


def patch(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        return 'skip'
    if text.count(ANCHOR) != 1:
        return f'anchor x{text.count(ANCHOR)}'
    text = text.replace(ANCHOR, RULE + ANCHOR, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return 'ok'


targets = [os.path.join(ROOT, 'generate_insights.py')]
for dirpath, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if not d.startswith(('.', '_'))]
    targets += [os.path.join(dirpath, n) for n in files if n.endswith('.html')]

for t in sorted(targets):
    print(f'{patch(t):10} {os.path.relpath(t, ROOT)}')
