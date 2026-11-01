#!/usr/bin/env python3
"""Saca pares inglés → español, párrafo a párrafo, de FineTranslations (spa_Latn).

El español es el original humano y el inglés, la traducción automática del
dataset: se usan al revés. Lee solo las columnas necesarias de unos pocos
ficheros repartidos al azar, sin descargarlos enteros.

Filtros:
- edu_score >= 2 (quita casi toda la basura web);
- documentos sin rasgos del español de España (vosotros, «os», ordenador…);
- trozos cuyas líneas coinciden en número en los dos idiomas;
- párrafos de 150 a 1500 caracteres, distintos en los dos idiomas;
- como mucho PER_DOC párrafos por documento, para que haya variedad.

Uso: .venv/bin/python scripts/fuentes/finetranslations.py salida.jsonl [pares] [ficheros]

Con sesión de Hugging Face (`hf auth login`) el límite de peticiones es mucho más alto.
"""
import json
import random
import re
import sys
import time

import urllib.request

import duckdb

from rasgos import spain_hits

REPO = 'hf://datasets/HuggingFaceFW/finetranslations'
TREE = 'https://huggingface.co/api/datasets/HuggingFaceFW/finetranslations/tree/main/data/spa_Latn'
FILES = 8
DOCS_PER_FILE = 1500
PER_DOC = 3
MIN_CHARS, MAX_CHARS = 150, 1500
SEED = 20261029
# Novelas traducidas por fans y páginas de juegos: textos ajenos y de mala calidad.
SKIP_URL = re.compile(r'novel|chapter|capitulo|manga|juego|game|letra|lyrics', re.I)


def shard_paths(rng, count):
    with urllib.request.urlopen(TREE, timeout=60) as r:
        files = sorted(x['path'] for x in json.load(r) if x['path'].endswith('.parquet'))
    return ['%s/%s' % (REPO, f) for f in rng.sample(files, count)]


def pairs_from(doc):
    for es_chunk, en_chunk in zip(doc['og_chunks'], doc['translated_chunks']):
        es_lines = [l.strip() for l in es_chunk.split('\n') if l.strip()]
        en_lines = [l.strip() for l in en_chunk.split('\n') if l.strip()]
        if len(es_lines) != len(en_lines):
            continue
        for es, en in zip(es_lines, en_lines):
            if MIN_CHARS <= len(es) <= MAX_CHARS and es != en and 0.6 < len(en) / len(es) < 1.5:
                yield en, es


def main():
    out, want = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    count = int(sys.argv[3]) if len(sys.argv) > 3 else FILES
    rng = random.Random(SEED)
    con = duckdb.connect()
    con.execute('CREATE SECRET hf (TYPE huggingface, PROVIDER credential_chain)')
    pairs = []
    for path in shard_paths(rng, count):
        if len(pairs) >= 3 * want:
            break
        try:
            rows = con.execute(
                'SELECT id, url, og_chunks, translated_chunks FROM read_parquet(?) WHERE edu_score >= 2 LIMIT ?',
                [path, DOCS_PER_FILE]).fetchall()
        except duckdb.Error as e:
            # Sin cuenta, Hugging Face limita las peticiones por IP: se espera y se pasa al siguiente.
            print('%s: %s' % (path.rsplit('/', 1)[1], str(e)[:120]), file=sys.stderr)
            time.sleep(120)
            continue
        kept = 0
        for doc_id, url, og, tr in rows:
            if SKIP_URL.search(url or '') or spain_hits(' '.join(og)):
                continue
            found = list(pairs_from({'og_chunks': og, 'translated_chunks': tr}))
            for en, es in rng.sample(found, min(PER_DOC, len(found))):
                pairs.append({'fuente': 'finetranslations', 'url': url, 'doc': doc_id, 'en': en, 'es': es})
                kept += 1
        print('%s: %d documentos, %d pares' % (path.rsplit('/', 1)[1], len(rows), kept), file=sys.stderr)
    rng.shuffle(pairs)
    with open(out, 'w') as f:
        for i, p in enumerate(pairs[:want], 1):
            f.write(json.dumps({'id': 'ft-%05d' % i, **p}, ensure_ascii=False) + '\n')
    print('%d pares en %s (de %d candidatos)' % (min(want, len(pairs)), out, len(pairs)), file=sys.stderr)


if __name__ == '__main__':
    main()
