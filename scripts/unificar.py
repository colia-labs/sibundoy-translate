#!/usr/bin/env python3
"""Une las fuentes abiertas del modelo base en un solo formato y aparta el examen.

Cada línea de salida: {"id", "fuente", "tipo", "formato", "url", "grupo", "en", "es"}.
- formato: "texto", "html" (solo <a href>, <em>, <strong>) o "markdown".
- grupo: el documento de origen. El examen aparta grupos enteros, para que
  ningún párrafo de un documento del examen se use para entrenar.

Global Voices se reparte entre los tres formatos. Un par con enlaces o
énfasis va a HTML o Markdown solo si los dos idiomas tienen los mismos
enlaces y el mismo número de cursivas y negritas; si no, queda como texto.
arXiv entra solo en el entrenamiento, desde datos/arxiv/final.jsonl (traducido
por los profesores y revisado): no tiene traducción humana con la que examinar.

Uso: python3 scripts/unificar.py
Escribe datos/base/entrenamiento.jsonl y datos/base/examen.jsonl.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / 'fuentes'))
import html_simple  # noqa: E402
from rasgos import spain_hits  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'datos' / 'fuentes'
OUT = ROOT / 'datos' / 'base'
SEED = 20261029
SHARE_HTML, SHARE_MARKDOWN = 0.45, 0.30
EXAM = {'finetranslations': 90, 'globalvoices': 70, 'tatoeba': 40}


def read(name):
    return [json.loads(l) for l in (SRC / name).open()]


def finetranslations():
    for r in read('finetranslations.jsonl'):
        yield {'fuente': 'finetranslations', 'tipo': 'parrafo', 'formato': 'texto', 'url': r['url'],
               'grupo': r['doc'], 'en': r['en'], 'es': r['es']}


def tatoeba():
    for r in read('tatoeba.jsonl'):
        yield {'fuente': 'tatoeba', 'tipo': 'frase', 'formato': 'texto', 'url': r['url'],
               'grupo': r['url'], 'en': r['en'], 'es': r['es']}


def globalvoices(rng):
    for r in read('globalvoices.jsonl'):
        en, es = html_simple.simplify(r['en']), html_simple.simplify(r['es'])
        if spain_hits(html_simple.to_text(es)):
            continue
        base = {'fuente': 'globalvoices', 'tipo': r['tipo'], 'url': r['url_en'], 'grupo': r['url_es']}
        marked = '<' in en or '<' in es
        roll = rng.random()
        if marked and html_simple.signature(en) == html_simple.signature(es) and roll < SHARE_HTML + SHARE_MARKDOWN:
            if roll < SHARE_HTML:
                yield {**base, 'formato': 'html', 'en': en, 'es': es}
            else:
                yield {**base, 'formato': 'markdown', 'en': html_simple.to_markdown(en), 'es': html_simple.to_markdown(es)}
        else:
            yield {**base, 'formato': 'texto', 'en': html_simple.to_text(en), 'es': html_simple.to_text(es)}


def arxiv():
    path = ROOT / 'datos' / 'arxiv' / 'final.jsonl'
    if not path.exists():
        return
    urls = json.loads((ROOT / 'datos' / 'arxiv' / 'urls.json').read_text())
    for r in map(json.loads, path.open()):
        url = urls[r['id'][:5]]
        yield {'fuente': 'arxiv', 'tipo': r['tipo'], 'formato': 'texto', 'url': url, 'grupo': url, 'en': r['en'], 'es': r['es']}


def exam_groups(rows, rng):
    """Grupos al azar de cada fuente hasta llegar a EXAM[fuente] pares."""
    chosen = set()
    for fuente, want in EXAM.items():
        groups = {}
        for r in rows:
            if r['fuente'] == fuente:
                groups.setdefault(r['grupo'], []).append(r)
        order = sorted(groups)
        rng.shuffle(order)
        n = 0
        for g in order:
            if n >= want:
                break
            chosen.add(g)
            n += len(groups[g])
    return chosen


def main():
    rng = random.Random(SEED)
    rows = list(finetranslations()) + list(tatoeba()) + list(globalvoices(rng))
    rows = [r for r in rows if r['en'].strip() and r['es'].strip() and r['en'] != r['es']]
    exam = exam_groups(rows, rng)
    rows += list(arxiv())
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}
    with (OUT / 'entrenamiento.jsonl').open('w') as train, (OUT / 'examen.jsonl').open('w') as test:
        for i, r in enumerate(rows, 1):
            split = 'examen' if r['grupo'] in exam else 'entrenamiento'
            (test if split == 'examen' else train).write(json.dumps({'id': 'b%05d' % i, **r}, ensure_ascii=False) + '\n')
            key = (split, r['fuente'], r['formato'])
            counts[key] = counts.get(key, 0) + 1
    for key in sorted(counts):
        print('%-14s %-17s %-9s %5d' % (*key, counts[key]))


if __name__ == '__main__':
    main()
