#!/usr/bin/env python3
"""Comprueba la traducción masiva con las mismas reglas que comprobar_cola.py.

Lee las unidades de ENTRADA (datos/masivo/entrada-N.jsonl o prueba.jsonl) y
lo traducido de SALIDA (datos/masivo/salida-NOMBRE.jsonl). Da el total de
trozos bien y mal, por motivo y por origen, y escribe en
datos/masivo/fallos-NOMBRE.jsonl los trozos con algún fallo duro, con sus
motivos, para que otro profesor los corrija.

Los fallos blandos (cifras distintas, Mayúscula En Cada Palabra, largo
extraño) no cuentan: en una muestra de la parte 1 casi todos eran
traducciones correctas, como «top 4» → «los cuatro finalistas» o un título
lleno de nombres propios.

Uso: .venv/bin/python scripts/comprobar_masivo.py ENTRADA SALIDA
"""
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/fuentes'))
import html_simple  # noqa: E402
from comprobador import check as check_text  # noqa: E402
from comprobar_arxiv import formulas, mask, title_case  # noqa: E402
from comprobar_cola import DIGITS, format_problem, plain  # noqa: E402

SOFT = re.compile(r'cifras distintas|Mayúscula En Cada Palabra|largo extraño')


def main():
    entrada, salida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    src = {}
    for u in map(json.loads, entrada.open()):
        for t in u['trozos']:
            src[t['id']] = {**t, 'origen': u['origen'], 'uid': u['uid']}
    got, modes = {}, collections.Counter()
    for r in map(json.loads, salida.open()):
        modes[r['modo']] += 1
        for t in r['trozos']:
            got[t['id']] = t
    problems = collections.defaultdict(list)
    for i, t in got.items():
        if not t['traduccion'] or t['fin'] != 'stop':
            problems[i].append('vacía o cortada (%s)' % t['fin'])

    def hide(i, text):
        return mask(text) if src[i]['origen'] == 'arxiv' else plain(text)

    ids = [i for i in got if got[i]['traduccion']]
    for i in ids:
        why = check_text(hide(i, src[i]['fuente']), hide(i, got[i]['traduccion']))
        if why:
            problems[i].append(why)
    for i in ids:
        s, t = src[i], got[i]['traduccion']
        if s['origen'] == 'arxiv':
            if sorted(formulas(s['fuente'])) != sorted(formulas(t)):
                problems[i].append('fórmulas distintas')
        else:
            p = format_problem(s['formato'], s['fuente'], t)
            if p:
                problems[i].append(p)
            if sorted(DIGITS.findall(html_simple.to_text(s['fuente']))) != sorted(DIGITS.findall(html_simple.to_text(t))):
                problems[i].append('cifras distintas')
        if s['tipo'] == 'titulo' and title_case(t):
            problems[i].append('Mayúscula En Cada Palabra')
    reasons, by_origin = collections.Counter(), collections.Counter()
    for i, ps in problems.items():
        by_origin[src[i]['origen']] += 1
        for p in ps:
            reasons[p.split(':')[0]] += 1
    hard = {i: ps for i, ps in problems.items() if any(not SOFT.search(p) for p in ps)}
    name = salida.stem.replace('salida-', '')
    with (salida.parent / ('fallos-%s.jsonl' % name)).open('w') as f:
        for i, ps in sorted(hard.items()):
            f.write(json.dumps({'id': i, 'uid': src[i]['uid'], 'motivos': ps}, ensure_ascii=False) + '\n')
    total = len(got)
    print('unidades: %s' % dict(modes))
    print('trozos traducidos: %d de %d; con problemas: %d (%.1f %%)' % (total, len(src), len(problems), 100 * len(problems) / max(total, 1)))
    print('con algún fallo duro (a corregir): %d (%.1f %%)' % (len(hard), 100 * len(hard) / max(total, 1)))
    print('por origen:', dict(by_origin))
    for p, n in reasons.most_common(12):
        print('  %5d  %s' % (n, p))


if __name__ == '__main__':
    main()
