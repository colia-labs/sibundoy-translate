#!/usr/bin/env python3
"""Puntúa las traducciones de un modelo con los dos exámenes.

Lee resultados/profesores/NOMBRE/traducciones.json (de colab/profesor.py o
de scripts/traducir_examenes.py) y da, por examen (base y wmt24pp), las
mismas medidas que evaluar.py: chrF, formato conservado y rasgos del
español de España, en total y por fuente y formato. En el examen base añade
el chrF solo de las referencias humanas (Global Voices y Tatoeba):
FineTranslations lo infla. Si existe comet.json (de colab/puntuar_comet.py), añade
COMET.

Con EXAMEN=datos/examenes/externos.jsonl puntúa los exámenes públicos de dominio.

Uso: .venv/bin/python scripts/puntuar_profesor.py NOMBRE [NOMBRE ...]
"""
import json
import os
import pathlib
import sys

import sacrebleu

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / 'fuentes'))
from evaluar import format_ok, summary  # noqa: E402
from rasgos import spain_hits  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
HUMAN = ('globalvoices', 'tatoeba')


def chrf(rows):
    return round(sacrebleu.corpus_chrf([x['salida'] for x in rows], [[x['es'] for x in rows]]).score, 2)


def main():
    exam = {r['id']: r for r in map(json.loads, (ROOT / os.environ.get('EXAMEN', 'datos/examenes/entrada.jsonl')).open())}
    for name in sys.argv[1:]:
        folder = ROOT / 'resultados/profesores' / name
        res = json.loads((folder / 'traducciones.json').read_text())
        comet = json.loads((folder / 'comet.json').read_text()) if (folder / 'comet.json').exists() else {}
        rows = []
        for t in res['filas']:
            r = exam[t['id']]
            rows.append({**r, 'salida': t['salida'], 'fin': t['fin'], 'formato_ok': format_ok(r, t['salida']),
                         'rasgos_espana': bool(spain_hits(t['salida'])), 'comet': comet.get(t['id'])})
        out = {'modelo': res['modelo'], 'segundos': res.get('segundos'), 'tokens': res.get('tokens'),
               'vacias': sum(not x['salida'] for x in rows)}
        exams = sorted({x['examen'] for x in rows})
        for name_exam in exams:
            sel = [x for x in rows if x['examen'] == name_exam]
            if not sel:
                continue
            s = summary(sel)
            if name_exam == 'base':
                s['humanas'] = {'chrf': chrf([x for x in sel if x['fuente'] in HUMAN])}
            scored = [x['comet'] for x in sel if x['comet'] is not None]
            if scored:
                s['total']['comet'] = round(100 * sum(scored) / len(scored), 2)
            out[name_exam] = s
        (folder / 'puntuacion.json').write_text(json.dumps({'resumen': out, 'filas': rows}, ensure_ascii=False, indent=1))
        print('== %s (%s) vacías %d, %s s' % (name, out['modelo'], out['vacias'], out['segundos']))
        for name_exam in exams:
            for k, v in out.get(name_exam, {}).items():
                print('  %-8s %-26s %s' % (name_exam, k, v))


if __name__ == '__main__':
    main()
