#!/usr/bin/env python3
"""Pares inglés → español de los resúmenes de SciELO (Latinoamérica).

Muchos artículos de SciELO traen el título y el resumen en español y en
inglés, escritos por sus autores: traducción humana. Solo entran revistas
con licencia CC BY (la API lo dice por revista, campo v541) y en vigor, de
las colecciones latinoamericanas; la de España queda fuera.

Casi siempre el original es el español y el inglés lo traduce el autor, a
veces con errores: se usa al revés, como FineTranslations (entra el inglés,
sale el español humano). Filtros: los dos lados en su idioma, largos
parecidos, sin rasgos del español de España.

Fase 1: revistas de cada colección, guardadas en datos/crudo/scielo/.
Fase 2: los POR_REVISTA artículos más recientes de cada revista CC BY.
Se puede cortar y relanzar: salta los artículos ya revisados.

Uso: python3 scielo.py salida.jsonl [por_revista]
"""
import concurrent.futures
import json
import pathlib
import re
import sys
import threading
import time
import urllib.request

from rasgos import spain_hits

API = 'https://articlemeta.scielo.org/api/v1'
AGENT = 'sibundoy-translate/1.0 (datos de entrenamiento CC BY; contacto: colia.org)'
COLLECTIONS = {'col': 'www.scielo.org.co', 'mex': 'www.scielo.org.mx', 'arg': 'www.scielo.org.ar',
               'chl': 'www.scielo.cl', 'per': 'www.scielo.org.pe', 'cri': 'www.scielo.sa.cr',
               'ury': 'www.scielo.edu.uy', 'cub': 'scielo.sld.cu', 'bol': 'www.scielo.org.bo',
               'ecu': 'scielo.senescyt.gob.ec', 'pry': 'scielo.iics.una.py', 'ven': 've.scielo.org',
               'dom': 'scielo.do'}
RAW = pathlib.Path(__file__).resolve().parents[2] / 'datos/crudo/scielo'
THREADS = 4
MIN_WORDS, MAX_WORDS = 50, 500
EN_WORDS = set('the and of to is that with for are was this were from by an these which'.split())
ES_WORDS = set('el la los las que de y en es por con para una del se fue'.split())


def get(url):
    for wait in (0, 10, 60, 180):
        time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            err = e
    print('sin respuesta: %s (%s)' % (url, err), file=sys.stderr)
    return None


def identifiers(kind, collection, issn=None):
    out, offset = [], 0
    while True:
        url = '%s/%s/identifiers/?collection=%s&limit=1000&offset=%d' % (API, kind, collection, offset)
        if issn:
            url += '&issn=' + issn
        d = get(url)
        if not d:
            return out
        out += [o['code'] for o in d['objects']]
        offset += 1000
        if offset >= d['meta']['total']:
            return out


def first(d, key):
    v = d.get(key) or [{}]
    return v[0].get('_')


def journals(collection):
    path = RAW / ('revistas-%s.json' % collection)
    if path.exists():
        return json.loads(path.read_text())
    out = []
    for issn in identifiers('journal', collection):
        j = get('%s/journal/?collection=%s&issn=%s' % (API, collection, issn))
        j = j[0] if isinstance(j, list) and j else j
        if not j:
            continue
        out.append({'issn': issn, 'titulo': first(j, 'v100'), 'licencia': first(j, 'v541'),
                    'estado': first(j, 'v50'), 'area': first(j, 'v441')})
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def looks(text, mine, other):
    words = re.findall(r'[a-záéíóúñü]+', text.lower())
    return sum(w in mine for w in words) > max(2, sum(w in other for w in words))


def by_lang(items):
    out = {}
    for x in items or []:
        if x.get('l') in ('es', 'en') and x.get('l') not in out:
            out[x['l']] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', x.get('a') or x.get('_') or '')).strip()
    return out


def pair(collection, journal, code):
    d = get('%s/article/?collection=%s&code=%s&format=xylose' % (API, collection, code))
    a = (d or {}).get('article') or {}
    abstracts, titles = by_lang(a.get('v83')), by_lang(a.get('v12'))
    if 'es' not in abstracts or 'en' not in abstracts:
        return None
    en, es = abstracts['en'], abstracts['es']
    if not (MIN_WORDS <= len(en.split()) <= MAX_WORDS) or not 0.8 <= len(es) / max(len(en), 1) <= 1.6:
        return None
    if not looks(en, EN_WORDS, ES_WORDS) or not looks(es, ES_WORDS, EN_WORDS) or spain_hits(es):
        return None
    return {'fuente': 'scielo', 'coleccion': collection, 'revista': journal['titulo'], 'area': journal['area'],
            'licencia': 'CC ' + journal['licencia'], 'idioma_original': first(a, 'v40'),
            'url': 'https://%s/scielo.php?script=sci_arttext&pid=%s' % (COLLECTIONS[collection], code),
            'titulo_en': titles.get('en'), 'titulo_es': titles.get('es'), 'en': en, 'es': es}


def main():
    out = pathlib.Path(sys.argv[1])
    per_journal = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    RAW.mkdir(parents=True, exist_ok=True)
    seen_path = RAW / 'articulos-revisados.txt'
    seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
    lock = threading.Lock()
    kept = 0
    # Al relanzar, las revistas que ya dieron pares no se repiten: si no, tomaría otros POR_REVISTA artículos.
    done = {(r['coleccion'], r['revista']) for r in map(json.loads, out.open())} if out.exists() else set()
    with out.open('a') as f, seen_path.open('a') as s:
        for collection in COLLECTIONS:
            # La licencia viene como «BY» o con versión, «BY/4.0».
            open_by = [j for j in journals(collection) if (j['licencia'] or '').upper().split('/')[0] == 'BY' and j['estado'] == 'C']
            print('%s: %d revistas CC BY en vigor' % (collection, len(open_by)), file=sys.stderr, flush=True)
            for j in open_by:
                if (collection, j['titulo']) in done:
                    continue
                # El pid lleva el año (S0120-41572014…): los más recientes primero.
                codes = sorted(set(identifiers('article', collection, j['issn'])) - seen, key=lambda c: c[10:14], reverse=True)
                with concurrent.futures.ThreadPoolExecutor(THREADS) as pool:
                    rows = list(pool.map(lambda c: (c, pair(collection, j, c)), codes[:per_journal]))
                with lock:
                    for code, row in rows:
                        s.write(code + '\n')
                        if row:
                            f.write(json.dumps(row, ensure_ascii=False) + '\n')
                            kept += 1
                    f.flush()
                    s.flush()
                print('  %s · %s: %d pares (total %d)' % (j['issn'], j['titulo'], sum(1 for _, r in rows if r), kept),
                      file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
