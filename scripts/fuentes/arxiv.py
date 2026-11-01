#!/usr/bin/env python3
"""Baja títulos y resúmenes de arXiv (metadatos CC0) para que los traduzca
el profesor. Reparte entre áreas para que haya variedad, no solo IA.

Usa OAI-PMH, la vía que arXiv recomienda para descargas en bloque: una
petición por área, con los artículos desde FROM, y 10 s entre peticiones.

Uso: python3 arxiv.py salida.jsonl [por_area] [desde AAAA-MM-DD]
"""
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

OAI = 'https://oaipmh.arxiv.org/oai?verb=ListRecords&metadataPrefix=arXiv&set=%s&from=%s'
FROM = '2026-10-01'
AREAS = ['cs', 'math', 'physics', 'astro-ph', 'cond-mat', 'quant-ph', 'q-bio', 'q-fin', 'stat', 'eess', 'econ']
NS = {'o': 'http://www.openarchives.org/OAI/2.0/', 'a': 'http://arxiv.org/OAI/arXiv/'}
DELAY = 10
AGENT = 'sibundoy-translate/1.0 (datos de entrenamiento; contacto: colia.org)'
SEED = 20261029


def fetch(url):
    for wait in (0, 30, 90, 180):
        time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            print('%d; espero' % e.code, file=sys.stderr)
    raise SystemExit('arXiv no responde')


def clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def main():
    out = sys.argv[1]
    per_area = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    since = sys.argv[3] if len(sys.argv) > 3 else FROM
    rng = random.Random(SEED)
    with open(out, 'w') as f:
        for area in AREAS:
            setspec = area if area in ('cs', 'math', 'stat', 'eess', 'econ', 'q-bio', 'q-fin') else 'physics:' + area
            if area == 'physics':
                setspec = 'physics'
            root = ET.fromstring(fetch(OAI % (setspec, since)))
            records = root.findall('.//o:record', NS)
            rows = []
            for r in records:
                m = r.find('.//a:arXiv', NS)
                if m is None:
                    continue
                rows.append({'fuente': 'arxiv', 'area': area, 'url': 'https://arxiv.org/abs/' + clean(m.findtext('a:id', namespaces=NS)),
                             'titulo': clean(m.findtext('a:title', namespaces=NS)), 'resumen': clean(m.findtext('a:abstract', namespaces=NS))})
            for row in rng.sample(rows, min(per_area, len(rows))):
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            print('%s: %d de %d' % (area, min(per_area, len(rows)), len(rows)), file=sys.stderr)
            time.sleep(DELAY)


if __name__ == '__main__':
    main()
