#!/usr/bin/env python3
"""Baja artículos de Global Voices en español con su original en inglés y
alinea sus párrafos (ver gv_alinear.py). Contenido bajo CC BY 3.0.

El español sale del feed paginado (trae el enlace «Ver artículo original») y
el inglés, de la API REST de WordPress. Respeta el Crawl-delay de 10 s de
robots.txt en los dos sitios. Se puede cortar y relanzar: salta los
artículos que ya están en la salida.

Uso: python3 globalvoices.py salida.jsonl [pares] [página_inicial]
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import gv_alinear

FEED = 'https://es.globalvoices.org/feed/?paged=%d'
REST = 'https://globalvoices.org/wp-json/wp/v2/posts?slug=%s&_fields=link,title,content'
DELAY = 10
AGENT = 'sibundoy-translate/1.0 (datos de entrenamiento CC BY; contacto: colia.org)'
ORIGINAL = re.compile(r"href=['\"](https://globalvoices\.org/\d{4}/\d\d/\d\d/([^/'\"]+)/?)['\"][^>]*>Ver artículo original")
NS = {'c': 'http://purl.org/rss/1.0/modules/content/'}
_last = 0.0


def fetch(url):
    global _last
    wait = DELAY - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def body(content):
    # Lo que sigue a los créditos es la firma de Global Voices, no el artículo.
    cut = content.find("<div class='text-credits")
    return content[:cut] if cut > 0 else content


def main():
    out = pathlib.Path(sys.argv[1])
    want = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    page = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    done, total = set(), 0
    if out.exists():
        for line in out.open():
            r = json.loads(line)
            done.add(r['url_es'])
            total += 1
    with out.open('a') as f:
        while total < want:
            items = ET.fromstring(fetch(FEED % page)).findall('.//item')
            if not items:
                break
            for item in items:
                url_es = item.findtext('link')
                content = item.findtext('c:encoded', namespaces=NS) or ''
                m = ORIGINAL.search(content)
                if url_es in done or not m:
                    continue
                try:
                    found = json.loads(fetch(REST % urllib.parse.quote(m.group(2))))
                except Exception as e:
                    print('salto %s: %s' % (m.group(1), e), file=sys.stderr)
                    continue
                if not found:
                    continue
                en = found[0]
                pairs = gv_alinear.align(gv_alinear.paragraphs(body(content)), gv_alinear.paragraphs(en['content']['rendered']))
                titles = [(item.findtext('title'), en['title']['rendered'])]
                for kind, rows in (('titulo', titles), ('parrafo', pairs)):
                    for es, en_text in rows:
                        f.write(json.dumps({'fuente': 'globalvoices', 'tipo': kind, 'url_es': url_es, 'url_en': m.group(1), 'en': en_text, 'es': es}, ensure_ascii=False) + '\n')
                        total += 1
                f.flush()
                print('página %d · %d pares · %s' % (page, total, url_es), file=sys.stderr)
            page += 1


if __name__ == '__main__':
    main()
