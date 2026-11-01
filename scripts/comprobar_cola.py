#!/usr/bin/env python3
"""Comprueba las traducciones de una sesión de la cola (datos/cola/N/salida/).

Cada trozo se comprueba según su origen:
- todos: que esté una sola vez y en español (comprobador.py), y
  que los títulos no lleven Mayúscula En Cada Palabra;
- arxiv: que las fórmulas $…$ sean idénticas (ver comprobar_arxiv.py);
- wikinews y plos: que estén las mismas cifras, y en wikinews que el formato
  (HTML, Markdown o texto) sea el del original.

Uso: python3 scripts/comprobar_cola.py SESIÓN [lote_NNNN ...]
"""
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

DIGITS = re.compile(r'\d+')


def markdown_signature(text):
    return (re.findall(r'\]\(([^)\s]+)\)', text), text.count('**'), text.count('*') - 2 * text.count('**'))


def plain(text):
    text = re.sub(r'\[([^\]]*)\]\([^)\s]+\)', r'\1', html_simple.to_text(text))
    return text.replace('<', ' menor ').replace('>', ' mayor ')


def unordered(signature):
    # En español el orden cambia («Lebanese Parliament» → «Parlamento libanés»), y los
    # enlaces se mueven con sus palabras: se comparan los enlaces, no su orden.
    links, *rest = signature
    return (sorted(links), *rest)


def format_problem(fmt, src, out):
    if fmt == 'html':
        if unordered(html_simple.signature(html_simple.simplify(out))) != unordered(html_simple.signature(src)):
            return 'los enlaces, <em> o <strong> no coinciden con el original'
    elif fmt == 'markdown':
        if unordered(markdown_signature(out)) != unordered(markdown_signature(src)):
            return 'los enlaces [texto](url), * o ** no coinciden con el original'
    elif re.search(r'<[a-z/]|\]\(', out):
        return 'el original es texto y la traducción lleva HTML o Markdown'
    return None


def check(name, src_path, out_path):
    src = {r['id']: r for r in map(json.loads, src_path.open())}
    problems, got = [], {}
    for i, line in enumerate(out_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(('línea %d' % i, 'JSON inválido (%s)' % e))
            continue
        if r.get('id') not in src:
            problems.append(('línea %d' % i, 'id desconocido %r' % r.get('id')))
        elif r['id'] in got:
            problems.append((r['id'], 'repetido'))
        else:
            got[r['id']] = r.get('traduccion', '')
    problems += [(i, 'falta') for i in src if i not in got]

    def hide(i, text):
        return mask(text) if src[i]['origen'] == 'arxiv' else plain(text)

    problems += [(i, why) for i, t in got.items() if (why := check_text(hide(i, src[i]['fuente']), hide(i, t)))]
    for i, t in got.items():
        s = src[i]
        if s['origen'] == 'arxiv':
            if sorted(formulas(s['fuente'])) != sorted(formulas(t)):
                problems.append((i, 'las fórmulas $…$ no coinciden con el original'))
        else:
            problem = format_problem(s['formato'], s['fuente'], t)
            if problem:
                problems.append((i, problem))
            if sorted(DIGITS.findall(html_simple.to_text(s['fuente']))) != sorted(DIGITS.findall(html_simple.to_text(t))):
                problems.append((i, 'las cifras no coinciden con el original'))
        if s['tipo'] == 'titulo' and title_case(t):
            problems.append((i, 'título con Mayúscula En Cada Palabra'))
    failed = {i for i, _ in problems if i in src}
    print('%s: %d de %d bien' % (name, len(src) - len(failed), len(src)))
    for i, p in problems:
        print('  %s: %s' % (i, p))
    return len(src), failed


def main():
    if len(sys.argv) < 2 or not (ROOT / 'datos/cola' / sys.argv[1]).is_dir():
        raise SystemExit('Uso: comprobar_cola.py SESIÓN [lote_NNNN ...]')
    base = ROOT / 'datos/cola' / sys.argv[1]
    names = sys.argv[2:] or sorted(p.stem for p in (base / 'salida').glob('lote_*.jsonl'))
    total = bad = 0
    for name in names:
        n, failed = check(name, base / 'lotes' / (name + '.jsonl'), base / 'salida' / (name + '.jsonl'))
        total += n
        bad += len(failed)
    print('Total: %d trozos con problemas de %d' % (bad, total))


if __name__ == '__main__':
    main()
