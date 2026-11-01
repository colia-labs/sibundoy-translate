#!/usr/bin/env python3
"""Correcciones de la traducción masiva de Gemma, hechas por otro profesor (GLM).

preparar: junta los trozos de datos/masivo/fallos-parte*.jsonl (de
  comprobar_masivo.py) en lotes de TAMAÑO trozos, en
  datos/masivo/correcciones/lotes/lote_NNN.jsonl, con el original, la
  traducción de Gemma y el motivo del fallo.
aplicar: comprueba cada salida del profesor con las reglas de la cola
  (comprobar_cola.check) y escribe en datos/masivo/correcciones.jsonl las
  correcciones que pasan, que unificar_v2.py usa en lugar del trozo de Gemma.

Uso: python3 scripts/correcciones_masivo.py preparar|aplicar [PROFESOR]
     PROFESOR (para aplicar): nombre del modelo que corrigió, p. ej. "GLM 5.3 Flash"
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from comprobar_cola import check  # noqa: E402

DIR = ROOT / 'datos/masivo/correcciones'
TAMAÑO = 50


def prepare():
    failed = {}
    for path in sorted((ROOT / 'datos/masivo').glob('fallos-parte*.jsonl')):
        for r in map(json.loads, path.open()):
            failed[r['id']] = r['motivos']
    rows = []
    for name in sorted(p.name.replace('fallos-', '') for p in (ROOT / 'datos/masivo').glob('fallos-parte*.jsonl')):
        part = name.replace('.jsonl', '').replace('parte', '')
        units = {u['uid']: u for u in map(json.loads, (ROOT / ('datos/masivo/entrada-%s.jsonl' % part)).open())}
        done = {t['id']: t for r in map(json.loads, (ROOT / ('datos/masivo/salida-parte%s.jsonl' % part)).open()) for t in r['trozos']}
        for u in units.values():
            for t in u['trozos']:
                if t['id'] in failed:
                    rows.append({'id': t['id'], 'origen': u['origen'], 'tipo': t['tipo'], 'formato': t['formato'],
                                 'fuente': t['fuente'], 'traduccion_actual': done.get(t['id'], {}).get('traduccion', ''),
                                 'problema': '; '.join(failed[t['id']])})
    (DIR / 'lotes').mkdir(parents=True, exist_ok=True)
    (DIR / 'salida').mkdir(exist_ok=True)
    for k in range(0, len(rows), TAMAÑO):
        with (DIR / 'lotes' / ('lote_%03d.jsonl' % (k // TAMAÑO + 1))).open('w') as f:
            for r in rows[k:k + TAMAÑO]:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('%d trozos en %d lotes' % (len(rows), -(-len(rows) // TAMAÑO)))


def apply(teacher):
    good = {}
    for out in sorted((DIR / 'salida').glob('lote_*.jsonl')):
        src = DIR / 'lotes' / out.name
        _, failed = check(out.stem, src, out)
        for line in out.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get('id') and r['id'] not in failed and r.get('traduccion'):
                good[r['id']] = {'id': r['id'], 'traduccion': r['traduccion'], 'profesor': teacher}
    with (ROOT / 'datos/masivo/correcciones.jsonl').open('w') as f:
        for r in good.values():
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('%d correcciones válidas en datos/masivo/correcciones.jsonl' % len(good))


if __name__ == '__main__':
    if sys.argv[1:2] == ['preparar']:
        prepare()
    elif sys.argv[1:2] == ['aplicar'] and len(sys.argv) > 2:
        apply(sys.argv[2])
    else:
        raise SystemExit(__doc__)
