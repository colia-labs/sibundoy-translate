#!/usr/bin/env python3
"""Prepara la traducción masiva con el profesor de Colab (Gemma 4 31B).

Toma las mismas unidades que la cola (preparar_cola.py): noticias de
Wikinews, arXiv, PLOS divulgación y PLOS ONE por áreas, y deja fuera:
- las de la sesión 1 de la cola, que traduce GLM en OpenCode;
- PLOS divulgación por encima de PLOS_DIVULGACION unidades, para no
  inclinar los datos hacia la biomedicina.

Cada unidad lleva sus trozos con el mismo formato que en la cola. El
formato de una noticia que no estaba en la cola se elige al azar con una
semilla propia de la unidad, así que no cambia entre ejecuciones.

Reparte las unidades en PARTES ficheros con un número parecido de palabras,
uno por VM: datos/masivo/entrada-N.jsonl, una unidad por línea:
{"uid", "origen", "fuente", "area", "url", "trozos": [{"id", "tipo", "formato", "fuente"}]}.

Uso: python3 scripts/preparar_masivo.py [--prueba N]
     --prueba N: solo N unidades variadas, en datos/masivo/prueba.jsonl
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from preparar_cola import SEED, lines, units, words  # noqa: E402

PARTES = 2
PLOS_DIVULGACION = 10000
OUT = ROOT / 'datos/masivo'


def pending():
    index = json.loads((ROOT / 'datos/cola/unidades.json').read_text())
    glm = {uid for uid, v in index.items() if v['sesion'] == 1}
    queued = {}
    for path in sorted((ROOT / 'datos/cola').glob('*/lotes/lote_*.jsonl')):
        for r in map(json.loads, path.open()):
            queued.setdefault(r['id'].rsplit('-', 1)[0], []).append(r)
    rng = random.Random(SEED)
    all_units = units()
    divulgacion = [u['uid'] for u in all_units if u['grupo'] == 'plos-divulgacion']
    keep = set(rng.sample(divulgacion, PLOS_DIVULGACION))
    out = []
    for u in all_units:
        if u['uid'] in glm or (u['grupo'] == 'plos-divulgacion' and u['uid'] not in keep):
            continue
        pieces = queued.get(u['uid']) or list(lines(u, random.Random('%d-%s' % (SEED, u['uid']))))
        out.append({'uid': u['uid'], 'origen': pieces[0]['origen'], 'fuente': u['fuente'], 'area': u['area'],
                    'url': u['url'], 'palabras': words(u),
                    'trozos': [{k: p[k] for k in ('id', 'tipo', 'formato', 'fuente')} for p in pieces]})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    todo = pending()
    random.Random(SEED).shuffle(todo)
    if len(sys.argv) > 2 and sys.argv[1] == '--prueba':
        n = int(sys.argv[2])
        by_origin = {}
        for u in todo:
            by_origin.setdefault(u['origen'], []).append(u)
        sample = [u for group in by_origin.values() for u in group[:-(-n // len(by_origin))]][:n]
        with (OUT / 'prueba.jsonl').open('w') as f:
            for u in sample:
                f.write(json.dumps(u, ensure_ascii=False) + '\n')
        print('%d unidades de prueba' % len(sample))
        return
    files = [(OUT / ('entrada-%d.jsonl' % (k + 1))).open('w') for k in range(PARTES)]
    load = [0] * PARTES
    for u in todo:
        k = load.index(min(load))
        files[k].write(json.dumps(u, ensure_ascii=False) + '\n')
        load[k] += u['palabras']
    for f in files:
        f.close()
    counts = {}
    for u in todo:
        counts[u['fuente']] = counts.get(u['fuente'], 0) + 1
    print('%d unidades, %d palabras, %d trozos' % (len(todo), sum(load), sum(len(u['trozos']) for u in todo)))
    print('por fuente:', counts)
    print('palabras por parte:', load)


if __name__ == '__main__':
    main()
