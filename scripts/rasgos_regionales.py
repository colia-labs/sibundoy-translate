#!/usr/bin/env python3
"""Cuenta rasgos regionales (España y zonas de Latinoamérica) en las traducciones.

Recorre resultados/profesores/*/traducciones.json y, para comparar, las
referencias humanas de los exámenes. Por modelo y examen da el porcentaje de
ítems con algún rasgo de España, con algún regionalismo latinoamericano y el
detalle por zona y palabra. Un traductor neutro debería quedar cerca de 0 en
ambos, y por debajo de la referencia.

Uso: .venv/bin/python scripts/rasgos_regionales.py [NOMBRE ...]   (sin nombres: todos)
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / 'fuentes'))
from rasgos import latam_hits, spain_hits  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMS = [ROOT / 'datos/examenes/entrada.jsonl', ROOT / 'datos/examenes/externos.jsonl']


def count(pairs):
    """pairs: lista de (examen, texto). Devuelve {examen: resumen}."""
    by = collections.defaultdict(list)
    for exam, text in pairs:
        by[exam].append(text)
    out = {}
    for exam, texts in sorted(by.items()):
        spain = [spain_hits(t) for t in texts]
        latam = [latam_hits(t) for t in texts]
        words = collections.Counter(w.lower() for hits in latam for _, w in hits)
        zones = collections.Counter(z for hits in latam for z in {z for z, _ in hits})
        out[exam] = {'n': len(texts), 'espana': sum(map(bool, spain)), 'latam': sum(map(bool, latam)),
                     'zonas': dict(zones.most_common()), 'palabras': dict(words.most_common(8))}
    return out


def show(name, res):
    for exam, r in res.items():
        print('%-28s %-10s n=%-5d España %5.1f %%  Latam %5.1f %%  %s %s' % (
            name, exam, r['n'], 100 * r['espana'] / r['n'], 100 * r['latam'] / r['n'], r['zonas'], r['palabras']))


def main():
    exam = {r['id']: r for path in EXAMS if path.exists() for r in map(json.loads, path.open())}
    show('REFERENCIA', count([(r['examen'], r['es']) for r in exam.values()]))
    folders = [ROOT / 'resultados/profesores' / n for n in sys.argv[1:]] or sorted(
        p.parent for p in (ROOT / 'resultados/profesores').glob('*/traducciones.json'))
    for folder in folders:
        rows = json.loads((folder / 'traducciones.json').read_text())['filas']
        show(folder.name, count([(exam[t['id']]['examen'], t['salida']) for t in rows if t['id'] in exam]))


if __name__ == '__main__':
    main()
