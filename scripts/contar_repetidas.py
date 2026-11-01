#!/usr/bin/env python3
"""Cuenta qué ítems de un examen aparecen en los datos de entrenamiento.

Un ítem cuenta como repetido si su texto en inglés, normalizado (minúsculas,
solo letras y cifras), está dentro de algún texto en inglés del entrenamiento,
o al revés. Sirve para saber qué parte de una nota es memoria y no traducción.

Escribe datos/examenes/repetidas-<examen>.json con los ids repetidos.

Uso: .venv/bin/python scripts/contar_repetidas.py EXAMEN.jsonl [ENTRENAMIENTO.jsonl]
"""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def main():
    exam = [json.loads(l) for l in open(sys.argv[1])]
    train_path = sys.argv[2] if len(sys.argv) > 2 else ROOT / 'datos/base-v2/entrenamiento.jsonl'
    train = [norm(json.loads(l)['en']) for l in open(train_path)]
    blob = '\n'.join(train)
    train_set = set(train)
    repeated = collections.defaultdict(list)
    total = collections.Counter()
    for r in exam:
        total[r['examen']] += 1
        t = norm(r['en'])
        # Las frases muy cortas («Thank you.») aparecen en cualquier sitio: solo cuentan si son un texto entero.
        if t in train_set or (len(t) >= 40 and t in blob):
            repeated[r['examen']].append(r['id'])
    for e in sorted(total):
        n = len(repeated[e])
        print('%-10s %4d de %4d repetidas (%.1f %%)' % (e, n, total[e], 100 * n / total[e]))
    out = ROOT / 'datos/examenes' / ('repetidas-%s.json' % pathlib.Path(sys.argv[1]).stem)
    out.write_text(json.dumps(repeated, indent=1))


if __name__ == '__main__':
    main()
