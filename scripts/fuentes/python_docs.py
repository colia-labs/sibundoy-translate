#!/usr/bin/env python3
"""Pares inglés → español de la traducción de la documentación de Python.

Los ficheros .po de github.com/python/python-docs-es ya traen cada párrafo
emparejado (msgid en inglés, msgstr en español). La documentación está bajo
la licencia de la PSF y los traductores ceden su trabajo a la PSF bajo CC0.

El marcado reST en línea pasa a Markdown igual en los dos idiomas:
``código`` → `código`, :rol:`texto <destino>` → `texto`,
`texto <url>`_ → [texto](url). Las entradas que no se traducen
(código, marcadas fuzzy o vacías) se saltan.

Uso: python3 python_docs.py carpeta_repo salida.jsonl [pares]
"""
import json
import pathlib
import random
import re
import sys

from rasgos import spain_hits

MIN_WORDS = 6
MAX_CHARS = 1500
SEED = 20261030
# El tutorial y las guías se parecen más a un artículo que la referencia de la API.
WEIGHT = {'tutorial': 3, 'howto': 3, 'faq': 3, 'whatsnew': 2, 'using': 2, 'installing': 2}
BRANCH = '3.14'

ROLE = re.compile(r':[a-z]+(?::[a-z]+)?:`(?:[^`<]*?<)?~?([^`>]+?)>?`')
LINK = re.compile(r'`([^`<]+?) <(https?://[^>]+)>`__?')
LITERAL = re.compile(r'``(.+?)``')


def entries(path):
    """(msgid, msgstr, fuzzy) de cada entrada del .po."""
    entry, field, fuzzy = {}, None, False
    for line in list(path.open(encoding='utf-8')) + ['\n']:
        line = line.rstrip('\n')
        if not line.strip():
            if entry.get('msgid'):
                yield entry['msgid'], entry.get('msgstr', ''), fuzzy
            entry, field, fuzzy = {}, None, False
        elif line.startswith('#,'):
            fuzzy = 'fuzzy' in line
        elif line.startswith('#'):
            continue
        elif line.startswith(('msgid ', 'msgstr ')):
            field, rest = line.split(' ', 1)
            entry[field] = json.loads(rest)
        elif line.startswith('"') and field:
            entry[field] += json.loads(line)


def to_markdown(text):
    text = LINK.sub(r'[\1](\2)', text)
    text = LITERAL.sub(r'`\1`', text)
    text = ROLE.sub(lambda m: '`%s`' % m.group(1).split('.')[-1] if '~' in m.group(0) else '`%s`' % m.group(1), text)
    text = re.sub(r'::$', ':', text.strip())
    return re.sub(r'\s+', ' ', text)


def usable(en, es):
    words = re.findall(r'[A-Za-z]{2,}', en)
    return (len(words) >= MIN_WORDS and len(en) <= MAX_CHARS and en != es
            and '\n' not in en.strip() and not en.lstrip().startswith(('>>>', '$', '..'))
            and all(en.count(c) == es.count(c) for c in '`*[') and not spain_hits(es))


def main():
    repo, out = pathlib.Path(sys.argv[1]), sys.argv[2]
    want = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
    pool = []
    for po in sorted(repo.rglob('*.po')):
        rel = po.relative_to(repo)
        if rel.parts[0] in ('cpython', '.overrides', '.migration'):
            continue
        weight = WEIGHT.get(rel.parts[0], 1)
        for msgid, msgstr, fuzzy in entries(po):
            if fuzzy or not msgstr.strip():
                continue
            en, es = to_markdown(msgid), to_markdown(msgstr)
            if usable(en, es):
                url = 'https://docs.python.org/es/%s/%s.html' % (BRANCH, rel.with_suffix('').as_posix())
                pool.append((weight, url, en, es))
    rng = random.Random(SEED)
    seen, chosen = set(), []
    # Muestreo ponderado sin reemplazo: clave u^(1/peso), las más altas ganan.
    for weight, url, en, es in sorted(pool, key=lambda p: rng.random() ** (1 / p[0]), reverse=True):
        if en not in seen:
            seen.add(en)
            chosen.append((url, en, es))
        if len(chosen) >= want:
            break
    with open(out, 'w') as f:
        for i, (url, en, es) in enumerate(chosen, 1):
            fmt = 'markdown' if '`' in en or '](' in en else 'texto'
            f.write(json.dumps({'id': 'py-%05d' % i, 'fuente': 'python-docs', 'formato': fmt, 'url': url,
                                'en': en, 'es': es}, ensure_ascii=False) + '\n')
    print('%d pares de %d candidatos' % (len(chosen), len(pool)), file=sys.stderr)


if __name__ == '__main__':
    main()
