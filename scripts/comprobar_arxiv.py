#!/usr/bin/env python3
"""Comprueba las traducciones de arXiv de datos/arxiv/salida/.

Por cada línea {"id", "traduccion"}:
- que esté y una sola vez;
- que el texto esté en español (ver comprobador.py);
- que las fórmulas entre $…$ sean idénticas a las del original;
- en los títulos, que no lleven Mayúscula En Cada Palabra.

Uso: python3 scripts/comprobar_arxiv.py [lote_NN ...]
     python3 scripts/comprobar_arxiv.py --correcciones
"""
import json
import pathlib
import re
import sys

from comprobador import check as check_text

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / 'datos/arxiv'
MATH = re.compile(r'\$[^$]+\$')
# Fórmulas de cualquier tipo: su «<» se tomaría por una etiqueta.
ANY_MATH = re.compile(r'\$[^$]+\$|\\\[.*?\\\]|\\\(.*?\\\)', re.S)


def formulas(text):
    # «$1.9 billion and … of $2.7» son dos dólares, no una fórmula: tiene palabras corridas.
    # «\$1,000» es un dólar escapado en LaTeX, nunca el inicio de una fórmula.
    text = text.replace('\\$', 'USD')
    return [m for m in MATH.findall(text) if not re.search(r'[A-Za-z]{3,} [A-Za-z]{3,} [A-Za-z]{3,}', m)]


def mask(text):
    # arXiv no trae HTML: un «<» suelto es notación («1<p\\leq\\infty»), no una etiqueta.
    return ANY_MATH.sub('X', text).replace('<', ' menor ').replace('>', ' mayor ')


def title_case(text):
    words = [w for w in re.findall(r'[^\W\d_][\w-]*', text) if len(w) > 3]
    caps = [w for w in words[1:] if w[0].isupper() and not w.isupper()]
    return len(words) > 3 and len(caps) / (len(words) - 1) > 0.5


def main():
    if sys.argv[1:] == ['--correcciones']:
        pairs = [('correcciones', DIR / 'correcciones/lote.jsonl', DIR / 'correcciones/salida.jsonl')]
    else:
        names = sys.argv[1:] or sorted(p.stem for p in (DIR / 'salida').glob('lote_*.jsonl'))
        pairs = [(n, DIR / 'lotes' / (n + '.jsonl'), DIR / 'salida' / (n + '.jsonl')) for n in names]
    total = bad = 0
    for name, src_path, out_path in pairs:
        src = {r['id']: r for r in map(json.loads, src_path.open())}
        problems, got = [], {}
        for i, line in enumerate(out_path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append('línea %d: JSON inválido (%s)' % (i, e))
                continue
            if r.get('id') not in src:
                problems.append('línea %d: id desconocido %r' % (i, r.get('id')))
            elif r['id'] in got:
                problems.append('%s: repetido' % r['id'])
            else:
                got[r['id']] = r.get('traduccion', '')
        problems += ['falta %s' % i for i in src if i not in got]
        for i, t in got.items():
            why = check_text(mask(src[i]['fuente']), mask(t))
            if why:
                problems.append('%s: %s' % (i, why))
        for i, t in got.items():
            if sorted(formulas(src[i]['fuente'])) != sorted(formulas(t)):
                problems.append('%s: las fórmulas $…$ no coinciden con el original' % i)
            if src[i]['tipo'] == 'titulo' and title_case(t):
                problems.append('%s: título con Mayúscula En Cada Palabra' % i)
        total += len(src)
        bad += len(problems)
        print('%s: %d de %d bien' % (name, len(src) - len(problems), len(src)))
        for p in problems:
            print('  ' + p)
    print('Total: %d problemas en %d trozos' % (bad, total))


if __name__ == '__main__':
    main()
