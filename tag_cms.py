"""Add data-cms keys to any untagged editable element in index.html.

Safe to re-run after editing index.html: existing keys are kept, new elements get
the next free number within their section, so content.json overrides stay valid.
"""
import collections, os, re

os.chdir(os.path.dirname(os.path.abspath(__file__)))
P = 'index.html'
s = open(P, encoding='utf-8').read()

existing = collections.defaultdict(int)
for m in re.finditer(r'data-cms(?:-img|-text|-href|-src)?="([a-zA-Z]+)-([a-z]+)(\d+)"', s):
    k = (m.group(1), m.group(2))
    existing[k] = max(existing[k], int(m.group(3)))


def nxt(sec, kind):
    existing[(sec, kind)] += 1
    return f'{sec}-{kind}{existing[(sec, kind)]}'


TAGS = 'h1|h2|h3|h4|p|span|strong|small|dt|dd|li|b|em|a|button|figcaption|legend'
SKIP_IDS = ('lightbox', 'request', 'progress', 'menu', 'mobile', 'subnav', 'dealerForm', 'dealerStatus')
main_start = s.index('<main>')
modal_end = s.index('<div class="lightbox"')
pattern = re.compile(r'<(?:section|div|nav)\b[^>]*\bid="([^"]+)"[^>]*>|<(img|iframe)\b([^>]*)>|<(%s)\b([^>]*)>([^<]*)</\4>' % TAGS)


def tag(seg, sec):
    out, pos = [], 0
    for m in pattern.finditer(seg):
        if m.group(1):
            if not m.group(1).startswith(SKIP_IDS):
                sec = m.group(1)
            continue
        if m.group(2):
            t, attrs = m.group(2), m.group(3)
            if 'data-cms' in attrs:
                continue
            if t == 'img' and 'src="assets/' in attrs:
                new = f'<img{attrs} data-cms-img="{nxt(sec, "img")}">'
            elif t == 'iframe':
                new = f'<iframe{attrs} data-cms-src="{nxt(sec, "src")}">'
            else:
                continue
        else:
            t, attrs, text = m.group(4), m.group(5), m.group(6)
            if 'data-cms' in attrs:
                continue
            if 'data-ko="' in attrs:
                new = f'<{t}{attrs} data-cms="{nxt(sec, "t")}">{text}</{t}>'
            elif t == 'a' and 'href="mailto:' in attrs:
                new = f'<a{attrs} data-cms-href="{nxt(sec, "href")}">{text}</a>'
            elif text.strip():
                new = f'<{t}{attrs} data-cms-text="{nxt(sec, "x")}">{text}</{t}>'
            else:
                continue
        out.append(seg[pos:m.start()])
        out.append(new)
        pos = m.end()
    out.append(seg[pos:])
    return ''.join(out)


new = s[:main_start] + tag(s[main_start:modal_end], 'hero') + s[modal_end:]
keys = re.findall(r'data-cms(?:-img|-text|-href|-src)?="([^"]+)"', new)
dups = [k for k, c in collections.Counter(keys).items() if c > 1]
assert not dups, dups
before = len(re.findall(r'data-cms(?:-img|-text|-href|-src)?="', s))
open(P, 'w', encoding='utf-8').write(new)
print('tagged total', len(keys), 'added', len(keys) - before)
