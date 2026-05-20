"""HTML-Whitelist-Sanitizer ohne externe Bibliothek."""
import re
import html as _html
from html.parser import HTMLParser

ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'caption', 'cite', 'code',
    'col', 'colgroup', 'dd', 'del', 'details', 'dfn', 'div', 'dl', 'dt',
    'em', 'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'i', 'img', 'ins', 'kbd', 'li', 'mark', 'ol', 'p', 'pre', 'q',
    's', 'samp', 'small', 'span', 'strong', 'sub', 'summary', 'sup',
    'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul', 'var',
}

ALLOWED_ATTRS = {
    'a': {'href', 'title', 'target', 'rel'},
    'img': {'src', 'alt', 'title', 'width', 'height'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan', 'scope'},
    'col': {'span'},
    '*': {'class', 'id', 'style'},
}

_URL_RE = re.compile(r'^(https?://|mailto:)', re.IGNORECASE)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        safe_attrs = self._filter_attrs(tag, dict(attrs))
        attr_str = ''.join(f' {k}="{_html.escape(v, quote=True)}"' for k, v in safe_attrs.items())
        self.result.append(f'<{tag}{attr_str}>')

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS:
            self.result.append(f'</{tag}>')

    def handle_data(self, data):
        self.result.append(data)

    def _filter_attrs(self, tag, attrs):
        allowed = ALLOWED_ATTRS.get('*', set()) | ALLOWED_ATTRS.get(tag, set())
        result = {}
        for key, value in attrs.items():
            if key.startswith('on') or key not in allowed:
                continue
            if key in ('href', 'src') and not _URL_RE.match(value or ''):
                continue
            result[key] = value
        if result.get('target') == '_blank':
            result['rel'] = 'noopener noreferrer'
        return result


def sanitize_html(html: str) -> str:
    if not html:
        return html
    parser = _Sanitizer()
    parser.feed(html)
    return ''.join(parser.result)
