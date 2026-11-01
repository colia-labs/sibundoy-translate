#!/usr/bin/env python3
"""Saca las noticias publicadas de la copia de Wikinews en inglés, párrafo a
párrafo, para que las traduzca el profesor. Licencia CC BY 4.0 (CC BY 2.5 en
las antiguas).

Cada párrafo queda en HTML simplificado (ver html_simple.py): los enlaces
internos apuntan a Wikinews, {{w|…}} a Wikipedia, y '''…''' y ''…'' pasan a
<strong> y <em>. Se corta en el primer título de sección (== Sources ==,
== Related news ==…) y se quitan imágenes, plantillas y referencias.

Uso: python3 wikinews.py copia.xml.bz2 salida.jsonl
"""
import bz2
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import mwparserfromhell

import html_simple

WIKINEWS = 'https://en.wikinews.org/wiki/'
WIKIPEDIA = 'https://en.wikipedia.org/wiki/'
SKIP_LINK = re.compile(r'^\s*:?\s*(file|image|category|media)\s*:', re.I)
DATE = re.compile(r'\{\{\s*date\s*\|\s*([^}|]+)', re.I)
MIN_PARAGRAPHS, MAX_PARAGRAPHS = 3, 40
MIN_CHARS = 60


def href(title, base):
    title = title.strip()
    for prefix, url in (('w:', WIKIPEDIA), ('wikipedia:', WIKIPEDIA)):
        if title.lower().startswith(prefix):
            title, base = title[len(prefix):], url
    return base + urllib.parse.quote(title.replace(' ', '_'), safe='/:()_,-.')


def link(url, text):
    return '<a href="%s">%s</a>' % (html.escape(url, quote=True), text)


def render(nodes):
    out = []
    for node in nodes:
        if isinstance(node, mwparserfromhell.nodes.Text):
            out.append(html.escape(str(node), quote=False))
        elif isinstance(node, mwparserfromhell.nodes.Wikilink):
            if SKIP_LINK.match(str(node.title)):
                continue
            text = render(node.text.nodes) if node.text else html.escape(str(node.title).strip(), quote=False)
            out.append(link(href(str(node.title), WIKINEWS), text))
        elif isinstance(node, mwparserfromhell.nodes.ExternalLink):
            if node.title:
                out.append(link(str(node.url), render(node.title.nodes)))
        elif isinstance(node, mwparserfromhell.nodes.Template):
            if str(node.name).strip().lower() == 'w' and node.params:
                target = str(node.params[0].value).strip()
                text = str(node.params[1].value).strip() if len(node.params) > 1 else target
                out.append(link(href(target, WIKIPEDIA), html.escape(text, quote=False)))
        elif isinstance(node, mwparserfromhell.nodes.Tag):
            tag = str(node.tag).lower()
            if tag in ('b', 'strong', 'i', 'em') and node.contents:
                name = 'strong' if tag in ('b', 'strong') else 'em'
                out.append('<%s>%s</%s>' % (name, render(node.contents.nodes), name))
            elif tag not in ('ref', 'br', 'gallery', 'table', 'math', 'syntaxhighlight') and node.contents:
                out.append(render(node.contents.nodes))
        elif isinstance(node, mwparserfromhell.nodes.HTMLEntity):
            out.append(html.escape(node.normalize(), quote=False))
    return ''.join(out)


def paragraphs(wikitext):
    body = re.split(r'\n\s*==', wikitext, maxsplit=1)[0]
    for block in re.split(r'\n\s*\n', body):
        block = block.strip()
        # Imágenes, plantillas sueltas, listas y tablas no son párrafos de la noticia.
        if not block or block[0] in '{[*#|:;!=' and not block.startswith('[[') or SKIP_LINK.match(block.lstrip('[')):
            continue
        simple = html_simple.simplify(render(mwparserfromhell.parse(block).nodes))
        if len(html_simple.to_text(simple)) >= MIN_CHARS:
            yield simple


def pages(path):
    for _, el in ET.iterparse(bz2.open(path), events=('end',)):
        name = el.tag.rsplit('}', 1)[-1]
        if name == 'page':
            ns = el.findtext('{*}ns')
            title = el.findtext('{*}title')
            text = el.findtext('{*}revision/{*}text') or ''
            redirect = el.find('{*}redirect') is not None
            el.clear()
            if ns == '0' and not redirect:
                yield title, text


def main():
    src, out = sys.argv[1], sys.argv[2]
    kept = seen = 0
    with open(out, 'w') as f:
        for title, text in pages(src):
            if not re.search(r'\{\{\s*publish(ed)?\s*\}\}', text, re.I):
                continue
            seen += 1
            paras = list(paragraphs(text))
            if not MIN_PARAGRAPHS <= len(paras) <= MAX_PARAGRAPHS:
                continue
            date = DATE.search(text)
            f.write(json.dumps({'fuente': 'wikinews', 'url': href(title, WIKINEWS), 'titulo': title,
                                'fecha': date.group(1).strip() if date else None, 'parrafos': paras},
                               ensure_ascii=False) + '\n')
            kept += 1
    print('%d noticias de %d publicadas' % (kept, seen), file=sys.stderr)


if __name__ == '__main__':
    main()
