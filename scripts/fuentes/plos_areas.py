#!/usr/bin/env python3
"""Baja resúmenes de PLOS ONE de las áreas que no cubren arXiv ni las otras
revistas de PLOS: psicología, educación, derecho, medicina clínica… Licencia
CC BY.

Por cada área, los PER_AREA artículos de investigación más recientes. Un
artículo que sale en varias áreas se guarda una vez, en la primera.
Respeta el límite de la API con DELAY s entre peticiones.

Uso: python3 plos_areas.py salida.jsonl [por_área]
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = 'https://api.plos.org/search?%s'
# Área en español: término de la clasificación de PLOS.
AREAS = {
    'psicologia': 'Psychology', 'educacion': 'Education', 'derecho': 'Law and legal sciences',
    'filosofia': 'Philosophy', 'economia': 'Economics', 'sociologia': 'Sociology',
    'medicina clinica': 'Clinical medicine', 'salud publica': 'Public and occupational health',
    'salud mental': 'Mental health and psychiatry', 'antropologia': 'Anthropology',
    'ciencia politica': 'Political science', 'linguistica': 'Linguistics',
}
DELAY = 10
AGENT = 'sibundoy-translate/1.0 (datos de entrenamiento CC BY; contacto: colia.org)'
MIN_WORDS, MAX_WORDS = 80, 450


def fetch(term, rows):
    query = urllib.parse.urlencode({
        'q': 'journal_key:PLoSONE AND doc_type:full AND article_type:"Research Article" AND subject:"%s"' % term,
        'fl': 'id,title,abstract,publication_date', 'rows': rows, 'sort': 'publication_date desc', 'wt': 'json'})
    for wait in (0, 60, 180):
        time.sleep(wait)
        try:
            req = urllib.request.Request(API % query, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)['response']['docs']
        except Exception as e:
            print('%s: %s; espero' % (term, e), file=sys.stderr)
    raise SystemExit('PLOS no responde')


def main():
    out = sys.argv[1]
    per_area = int(sys.argv[2]) if len(sys.argv) > 2 else 800
    seen = set()
    with open(out, 'w') as f:
        for area, term in AREAS.items():
            kept = 0
            for doc in fetch(term, per_area):
                text = re.sub(r'\s+', ' ', ' '.join(doc.get('abstract') or [])).strip()
                if doc['id'] in seen or not MIN_WORDS <= len(text.split()) <= MAX_WORDS:
                    continue
                seen.add(doc['id'])
                f.write(json.dumps({'fuente': 'plos-one', 'area': area, 'url': 'https://doi.org/' + doc['id'],
                                    'fecha': doc.get('publication_date', '')[:10],
                                    'titulo': re.sub(r'\s+', ' ', doc.get('title', '')).strip(), 'resumen': text},
                                   ensure_ascii=False) + '\n')
                kept += 1
            print('%s: %d' % (area, kept), file=sys.stderr)
            time.sleep(DELAY)


if __name__ == '__main__':
    main()
