#!/usr/bin/env python3
"""Parte los títulos y resúmenes de arXiv en lotes para el profesor.

Cada lote lleva ARTICLES artículos: una línea por título y otra por resumen,
{"id", "tipo", "fuente"}. Los ids son a0001-t (título) y a0001-r (resumen).

Uso: python3 scripts/preparar_arxiv.py
     python3 scripts/preparar_arxiv.py --nuevos fichero.jsonl [artículos]
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLES = 30
SEED = 20261029


def add(path, want):
    """Añade lotes nuevos tras los que ya existen, sin tocar los anteriores.

    Salta los artículos que ya están en urls.json y reparte por igual entre áreas.
    """
    index = json.loads((ROOT / 'datos/arxiv/urls.json').read_text())
    known = set(index.values())
    by_area = {}
    for r in map(json.loads, open(path)):
        if r['url'] not in known:
            known.add(r['url'])
            by_area.setdefault(r['area'], []).append(r)
    rng = random.Random(SEED + 1)
    per_area = -(-want // len(by_area))
    rows = []
    for area in sorted(by_area):
        rows += rng.sample(by_area[area], min(per_area, len(by_area[area])))
    rng.shuffle(rows)
    rows = rows[:want]
    out = ROOT / 'datos/arxiv/lotes'
    # Los lotes 23 a 42 pasaron a la cola (datos/arxiv/lotes-cola/): sus números no se repiten.
    taken = list(out.glob('lote_*.jsonl')) + list((ROOT / 'datos/arxiv/lotes-cola').glob('lote_*.jsonl'))
    first = max(int(p.stem.split('_')[1]) for p in taken) + 1
    next_id = max(int(k[1:]) for k in index) + 1
    for n, start in enumerate(range(0, len(rows), ARTICLES), first):
        with (out / ('lote_%02d.jsonl' % n)).open('w') as f:
            for k, r in enumerate(rows[start:start + ARTICLES], next_id + start):
                aid = 'a%04d' % k
                index[aid] = r['url']
                f.write(json.dumps({'id': aid + '-t', 'tipo': 'titulo', 'fuente': r['titulo']}, ensure_ascii=False) + '\n')
                f.write(json.dumps({'id': aid + '-r', 'tipo': 'resumen', 'fuente': r['resumen']}, ensure_ascii=False) + '\n')
    (ROOT / 'datos/arxiv/urls.json').write_text(json.dumps(index, indent=1))
    print('%d artículos nuevos en los lotes %02d a %02d' % (len(rows), first, first + -(-len(rows) // ARTICLES) - 1))


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--nuevos':
        add(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600)
        return
    rows = [json.loads(l) for l in (ROOT / 'datos/fuentes/arxiv.jsonl').open()]
    random.Random(SEED).shuffle(rows)
    index = {}
    out = ROOT / 'datos/arxiv/lotes'
    for start in range(0, len(rows), ARTICLES):
        with (out / ('lote_%02d.jsonl' % (start // ARTICLES + 1))).open('w') as f:
            for k, r in enumerate(rows[start:start + ARTICLES], start + 1):
                aid = 'a%04d' % k
                index[aid] = r['url']
                f.write(json.dumps({'id': aid + '-t', 'tipo': 'titulo', 'fuente': r['titulo']}, ensure_ascii=False) + '\n')
                f.write(json.dumps({'id': aid + '-r', 'tipo': 'resumen', 'fuente': r['resumen']}, ensure_ascii=False) + '\n')
    (ROOT / 'datos/arxiv/urls.json').write_text(json.dumps(index, indent=1))
    print('%d artículos en %d lotes' % (len(rows), -(-len(rows) // ARTICLES)))


if __name__ == '__main__':
    main()
