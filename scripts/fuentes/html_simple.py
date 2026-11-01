"""Simplifica el HTML de un párrafo a enlaces, cursivas y negritas, y lo pasa
a Markdown o a texto plano.

Solo quedan `<a href>`, `<em>` y `<strong>`: `<i>` pasa a `<em>` y `<b>` a
`<strong>`. El resto de etiquetas (`span`, `br`, `script`…) se quitan y su
texto se conserva, salvo el de `script` y `style`.
"""
import html
import re
from html.parser import HTMLParser

RENAME = {'em': 'em', 'i': 'em', 'strong': 'strong', 'b': 'strong'}
DROP_TEXT = {'script', 'style'}


class _Simplifier(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_TEXT:
            self.skip += 1
            return
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.out.append('<a href="%s">' % html.escape(href, quote=True))
                self.stack.append('a')
                return
        elif tag in RENAME:
            self.out.append('<%s>' % RENAME[tag])
            self.stack.append(RENAME[tag])
            return
        self.stack.append(None)

    def handle_endtag(self, tag):
        if tag in DROP_TEXT:
            self.skip = max(0, self.skip - 1)
            return
        if self.stack:
            kept = self.stack.pop()
            if kept:
                self.out.append('</%s>' % kept)

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def simplify(fragment):
    p = _Simplifier()
    p.feed(fragment)
    p.close()
    text = ''.join(p.out)
    # Etiquetas vacías y espacios repetidos que deja quitar el formato.
    text = re.sub(r'<(em|strong)>(\s*)</\1>', r'\2', text)
    text = re.sub(r'<a href="[^"]*">(\s*)</a>', r'\1', text)
    # Los espacios del borde salen fuera de la etiqueta: «will[ host…](…)» en Markdown.
    text = re.sub(r'(<(?:a href="[^"]*"|em|strong)>)(\s+)', r'\2\1', text)
    text = re.sub(r'(\s+)(</(?:a|em|strong)>)', r'\2\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def signature(simple):
    """Lo que debe coincidir entre original y traducción: los enlaces en orden
    y cuántas cursivas y negritas hay."""
    return (re.findall(r'<a href="([^"]*)">', simple), simple.count('<em>'), simple.count('<strong>'))


def to_markdown(simple):
    text = re.sub(r'<a href="([^"]*)">(.*?)</a>', lambda m: '[%s](%s)' % (m.group(2), html.unescape(m.group(1))), simple)
    text = re.sub(r'</?strong>', '**', text)
    text = re.sub(r'</?em>', '*', text)
    return html.unescape(text)


def to_text(simple):
    return html.unescape(re.sub(r'<[^>]+>', '', simple)).strip()
