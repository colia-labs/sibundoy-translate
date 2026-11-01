#!/usr/bin/env python3
"""Junta los dos exámenes en datos/examenes/entrada.jsonl.

- base: el examen público del modelo base (datos/base/examen.jsonl).
- wmt24pp: WMT24++ inglés → español de México (google/wmt24pp, Apache 2.0),
  sin la línea de control (canary) ni las frases que sus autores marcaron
  como mal originales (is_bad_source). Dominios: social, literario,
  noticias y discursos.

WMT24++ solo sirve para examinar: nunca entra en el entrenamiento.

Uso: python3 scripts/preparar_examenes.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'datos/examenes'
    out.mkdir(exist_ok=True)
    n = {'base': 0, 'wmt24pp': 0}
    with (out / 'entrada.jsonl').open('w') as f:
        for r in map(json.loads, (ROOT / 'datos/base/examen.jsonl').open()):
            f.write(json.dumps({'id': r['id'], 'examen': 'base', 'fuente': r['fuente'], 'formato': r['formato'],
                                'en': r['en'], 'es': r['es']}, ensure_ascii=False) + '\n')
            n['base'] += 1
        for r in map(json.loads, (ROOT / 'datos/wmt24pp/en-es_MX.jsonl').open()):
            if r['is_bad_source'] or r['domain'] == 'canary':
                continue
            f.write(json.dumps({'id': 'wmt-%03d' % r['segment_id'], 'examen': 'wmt24pp', 'fuente': r['domain'],
                                'formato': 'texto', 'en': r['source'], 'es': r['target']}, ensure_ascii=False) + '\n')
            n['wmt24pp'] += 1
    print(n)


if __name__ == '__main__':
    main()
