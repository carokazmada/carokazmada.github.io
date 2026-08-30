from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.h1_count = 0
        self.images_without_alt = []
        self.inline_handlers = []
        self.unsafe_blank_links = []
        self.meta = set()
        self.links = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'title':
            self._in_title = True
        elif tag == 'h1':
            self.h1_count += 1
        elif tag == 'img' and not attrs_dict.get('alt', '').strip():
            self.images_without_alt.append(attrs_dict.get('src', '(inline image)'))
        elif tag == 'meta':
            key = attrs_dict.get('name') or attrs_dict.get('property')
            if key:
                self.meta.add(key.lower())
        elif tag == 'a':
            href = attrs_dict.get('href', '')
            self.links.append(href)
            if attrs_dict.get('target') == '_blank':
                rel = set((attrs_dict.get('rel') or '').lower().split())
                if 'noopener' not in rel:
                    self.unsafe_blank_links.append(href)
        for name in attrs_dict:
            if name.lower().startswith('on'):
                self.inline_handlers.append(name)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


html = Path('index.html').read_text(encoding='utf-8')
parser = SiteParser()
parser.feed(html)
errors = []
if not parser.title.strip():
    errors.append('missing title')
if parser.h1_count != 1:
    errors.append(f'expected exactly one h1, found {parser.h1_count}')
for required in ('description', 'og:title', 'og:description', 'og:image', 'twitter:card'):
    if required not in parser.meta:
        errors.append(f'missing meta {required}')
if parser.images_without_alt:
    errors.append(f'images without alt: {parser.images_without_alt[:3]}')
if parser.inline_handlers:
    errors.append(f'inline event handlers: {parser.inline_handlers}')
if parser.unsafe_blank_links:
    errors.append(f'unsafe target=_blank links: {parser.unsafe_blank_links[:3]}')
for href in parser.links:
    if href.startswith('http://'):
        errors.append(f'non-HTTPS link: {href}')

if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: title, one h1, SEO/social metadata, {len(parser.images_without_alt)} image alt gaps, no inline handlers, and safe external links')
