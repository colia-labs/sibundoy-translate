#!/usr/bin/env python3
"""Baja los resúmenes para el público («Author summary») de las revistas de
PLOS que los publican, para que los traduzca el profesor. Licencia CC BY.

La API de PLOS no los trae en un campo propio: van en `abstract`, tras el
resumen técnico y la marca «Author summary:». Solo se guardan los artículos
que la tienen.

Respeta el límite de la API (10 peticiones por minuto) con DELAY s entre
peticiones. Se puede cortar y relanzar: salta las revistas ya completas.

Uso: python3 plos.py salida.jsonl
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

API = 'https://api.plos.org/search?%s'
JOURNALS = ['PLoSBiology', 'PLoSGenetics', 'PLoSCompBiol', 'PLoSPathogens', 'PLoSNTD']
ROWS = 1000
DELAY = 10
AGENT = 'sibundoy-translate/1.0 (datos de entrenamiento CC BY; contacto: colia.org)'
MARK = re.compile(r'\n\s*Author summary:?\s*', re.I)
MIN_WORDS, MAX_WORDS = 60, 400


def fetch(journal, start):
    query = urllib.parse.urlencode({
        'q': 'journal_key:%s AND doc_type:full AND article_type:"Research Article"' % journal,
        'fl': 'id,title,abstract,publication_date', 'rows': ROWS, 'start': start,
        'sort': 'publication_date desc', 'wt': 'json'})
    for wait in (0, 60, 180):
        time.sleep(wait)
        try:
            req = urllib.request.Request(API % query, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)['response']
        except Exception as e:
            print('%s %d: %s; espero' % (journal, start, e), file=sys.stderr)
    raise SystemExit('PLOS no responde')


def summary(doc):
    text = ' '.join(doc.get('abstract') or [])
    parts = MARK.split(text, maxsplit=1)
    if len(parts) < 2:
        return None
    s = re.sub(r'\s+', ' ', parts[1]).strip()
    return s if MIN_WORDS <= len(s.split()) <= MAX_WORDS else None


def main():
    out = pathlib.Path(sys.argv[1])
    done = set()
    if out.exists():
        done = {json.loads(l)['revista'] for l in out.open()}
    with out.open('a') as f:
        for journal in JOURNALS:
            if journal in done:
                continue
            # Se escribe la revista entera al final: una revista a medias no queda marcada como hecha.
            start, rows, found = 0, [], None
            while found is None or start < found:
                resp = fetch(journal, start)
                found = resp['numFound']
                for doc in resp['docs']:
                    s = summary(doc)
                    if s:
                        rows.append({'fuente': 'plos', 'revista': journal, 'url': 'https://doi.org/' + doc['id'],
                                     'fecha': doc.get('publication_date', '')[:10],
                                     'titulo': re.sub(r'\s+', ' ', doc.get('title', '')).strip(), 'resumen': s})
                start += ROWS
                print('%s: %d de %d revisados, %d con resumen para el público' % (journal, min(start, found), found, len(rows)), file=sys.stderr)
                time.sleep(DELAY)
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()


if __name__ == '__main__':
    main()
