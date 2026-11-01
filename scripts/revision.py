#!/usr/bin/env python3
"""Revisión de las traducciones de arXiv: Claude marca, el profesor corrige.

Ningún texto escrito por Claude entra en los datos: los revisores solo
dicen «bien» o «error» con un motivo, y la corrección la escribe un profesor.

Modos:
  paquetes N      parte todos los trozos traducidos en N paquetes para los
                  revisores: datos/arxiv/revision/paquete_K.jsonl, con
                  {"id", "tipo", "en", "es"}.
  correcciones    junta los errores confirmados (confirmados.jsonl:
                  {"id", "problema"}) en datos/arxiv/correcciones/lote.jsonl,
                  con el original, la traducción actual y el problema.
  aplicar         aplica las rondas de correcciones (salida_N.jsonl y salida.jsonl)
                  ({"id", "traduccion"}) y escribe datos/arxiv/final.jsonl.

Uso: python3 scripts/revision.py MODO [N]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / 'datos/arxiv'


def pieces():
    src, out = {}, {}
    for f in sorted((DIR / 'lotes').glob('lote_*.jsonl')):
        for r in map(json.loads, f.open()):
            src[r['id']] = r
    for f in sorted((DIR / 'salida').glob('lote_*.jsonl')):
        for r in map(json.loads, f.open()):
            out[r['id']] = r['traduccion']
    return [{'id': i, 'tipo': src[i]['tipo'], 'en': src[i]['fuente'], 'es': out[i]} for i in sorted(src) if i in out]


def write_jsonl(path, rows):
    with path.open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def main():
    mode = sys.argv[1]
    rows = pieces()
    if mode == 'paquetes':
        n = int(sys.argv[2])
        # Por artículo, para que título y resumen vayan juntos al mismo revisor.
        arts = sorted({r['id'][:5] for r in rows})
        for k in range(n):
            mine = set(arts[k::n])
            write_jsonl(DIR / 'revision' / ('paquete_%d.jsonl' % (k + 1)), [r for r in rows if r['id'][:5] in mine])
        print('%d trozos en %d paquetes' % (len(rows), n))
    elif mode == 'correcciones':
        by_id = {r['id']: r for r in rows}
        flagged = [json.loads(l) for l in (DIR / 'revision/confirmados.jsonl').open()]
        write_jsonl(DIR / 'correcciones/lote.jsonl',
                    [{'id': f['id'], 'tipo': by_id[f['id']]['tipo'], 'fuente': by_id[f['id']]['en'],
                      'traduccion_actual': by_id[f['id']]['es'], 'problema': f['problema']} for f in flagged])
        print('%d trozos para corregir' % len(flagged))
    elif mode == 'aplicar':
        # Las rondas se aplican en orden: una ronda posterior gana a la anterior.
        fixed = {}
        for path in sorted((DIR / 'correcciones').glob('salida_*.jsonl')) + [DIR / 'correcciones/salida.jsonl']:
            if path.exists():
                fixed.update({r['id']: r['traduccion'] for r in map(json.loads, path.open())})
        write_jsonl(DIR / 'final.jsonl', [{**r, 'es': fixed.get(r['id'], r['es']), 'corregido': r['id'] in fixed} for r in rows])
        print('%d trozos, %d corregidos' % (len(rows), len(fixed)))


if __name__ == '__main__':
    main()
