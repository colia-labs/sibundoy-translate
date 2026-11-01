#!/usr/bin/env python3
"""Arma la mezcla de entrenamiento del modelo base v2.

Junta las fuentes humanas y las traducidas por profesores, quita todo lo que
toque el examen de la v1 (datos/base/examen.jsonl, que no cambia, para
comparar) y toma de cada fuente como mucho CUPOS[fuente] pares al azar, para
que ninguna domine la mezcla.

Fuentes humanas: FineTranslations, Global Voices reciente (repartido entre
HTML, Markdown y texto como en la v1), Global Voices de OPUS, documentación
de Python, Tatoeba y SciELO (título y resumen, sin la etiqueta «Resumen.»).
Fuentes de profesores: arXiv (DeepSeek, GLM y MiniMax en la v1; GLM y Gemma
en la v2), la cola de GLM (sesión 1) y la traducción masiva de Gemma 4 31B.
De los profesores solo entran trozos que pasaron su comprobador: los de la
traducción masiva que están en datos/masivo/fallos-*.jsonl quedan fuera
salvo que tengan corrección en datos/masivo/correcciones.jsonl.

Uso: python3 scripts/unificar_v2.py [--solo-contar]
Escribe datos/base-v2/entrenamiento.jsonl, con los mismos campos que la v1
más "profesor".
"""
import collections
import html
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / 'fuentes'))
import unificar  # noqa: E402
from rasgos import spain_hits  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'datos/base-v2'
SEED = 20261030
# Noticias, general y ciencia, cada grupo alrededor de un tercio (acordado con Rubén el 2026-10-30).
CUPOS = {
    'wikinews': 12000, 'globalvoices': 9000, 'opus-globalvoices': 3000,
    'finetranslations': 20000, 'tatoeba': 2500,
    'plos': 10000, 'scielo': 8000, 'arxiv': 6000,
    'python-docs': 3000,
}
WORD = re.compile(r'[^\W\d_]+')
LABEL = re.compile(r'^\s*(abstract|summary|resumen|sumario|introducción|introduction)\s*[.:\-–]?\s*', re.I)


def untranslated(en, es):
    """El «español» repite casi todas las palabras del inglés: una cita sin traducir,
    un título en inglés o una lista de nombres."""
    plain = lambda t: WORD.findall(re.sub(r'<[^>]+>|\]\([^)]*\)', ' ', t).lower())
    a, b = plain(en), plain(es)
    return len(b) >= 4 and sum(w in set(a) for w in b) / len(b) > 0.6


def read(path):
    path = ROOT / path
    return [json.loads(l) for l in path.open()] if path.exists() else []


def human():
    rng = random.Random(SEED)
    yield from unificar.finetranslations()
    yield from unificar.tatoeba()
    yield from unificar.globalvoices(rng)
    for r in read('datos/fuentes/opus-gv.jsonl'):
        yield {'fuente': 'opus-globalvoices', 'tipo': 'parrafo', 'formato': 'texto', 'url': r['url'],
               'grupo': r['id'], 'en': r['en'], 'es': r['es']}
    for r in read('datos/fuentes/python-docs.jsonl'):
        yield {'fuente': 'python-docs', 'tipo': 'parrafo', 'formato': r['formato'], 'url': r['url'],
               'grupo': r['url'], 'en': r['en'], 'es': r['es']}
    # SciELO trae entidades HTML (&#8217;) en títulos y resúmenes.
    for r in read('datos/fuentes/scielo.jsonl'):
        if r.get('titulo_en') and r.get('titulo_es') and not spain_hits(r['titulo_es']):
            yield {'fuente': 'scielo', 'tipo': 'titulo', 'formato': 'texto', 'url': r['url'], 'grupo': r['url'],
                   'area': r['area'], 'en': html.unescape(r['titulo_en']), 'es': html.unescape(r['titulo_es'])}
        yield {'fuente': 'scielo', 'tipo': 'resumen', 'formato': 'texto', 'url': r['url'], 'grupo': r['url'],
               'area': r['area'], 'en': LABEL.sub('', html.unescape(r['en'])), 'es': LABEL.sub('', html.unescape(r['es']))}


def teacher_pieces():
    """{id del trozo: (traducción, profesor)} de todo lo que pasó su comprobador."""
    out = {}
    for path in sorted((ROOT / 'datos/cola/1/salida').glob('lote_*.jsonl')):
        for r in map(json.loads, path.open()):
            out[r['id']] = (r['traduccion'], 'GLM 5.3 Flash')
    failed = set()
    for path in (ROOT / 'datos/masivo').glob('fallos-parte*.jsonl'):
        failed |= {json.loads(l)['id'] for l in path.open()}
    fixes = {r['id']: (r['traduccion'], r['profesor']) for r in read('datos/masivo/correcciones.jsonl')}
    for path in sorted((ROOT / 'datos/masivo').glob('salida-parte*.jsonl')):
        for r in map(json.loads, path.open()):
            for t in r['trozos']:
                if t['id'] in out:
                    continue
                if t['id'] in fixes:
                    out[t['id']] = fixes[t['id']]
                elif t['id'] not in failed and t['traduccion'] and t['fin'] == 'stop':
                    out[t['id']] = (t['traduccion'], 'Gemma 4 31B')
    return out


def teacher():
    pieces = teacher_pieces()
    index = json.loads((ROOT / 'datos/cola/unidades.json').read_text())
    sources = {}
    for path in sorted((ROOT / 'datos/masivo').glob('entrada-*.jsonl')):
        for u in map(json.loads, path.open()):
            sources[u['uid']] = u
    for path in sorted((ROOT / 'datos/cola/1/lotes').glob('lote_*.jsonl')):
        for t in map(json.loads, path.open()):
            uid = t['id'].rsplit('-', 1)[0]
            sources.setdefault(uid, {'uid': uid, 'url': index[uid]['url'], 'fuente': index[uid]['fuente'],
                                     'area': index[uid]['area'], 'trozos': []})
            if t['id'] not in {x['id'] for x in sources[uid]['trozos']}:
                sources[uid]['trozos'].append(t)
    for u in sources.values():
        fuente = {'wikinews': 'wikinews', 'arxiv': 'arxiv'}.get(u['fuente'], 'plos')
        for t in u['trozos']:
            if t['id'] in pieces:
                es, prof = pieces[t['id']]
                yield {'fuente': fuente, 'tipo': t['tipo'], 'formato': t['formato'], 'url': u['url'], 'grupo': u['uid'],
                       'area': u['area'], 'profesor': prof, 'en': t['fuente'], 'es': es}
    # arXiv de la v1 (datos/arxiv/final.jsonl) y lotes de GLM a partir del 43, comprobados con comprobar_arxiv.py.
    for r in unificar.arxiv():
        yield {**r, 'profesor': 'DeepSeek V4.1 Flash, GLM 5.3 Flash o MiniMax M3 (ver datos/arxiv/PROFESORES.md)'}
    urls = json.loads((ROOT / 'datos/arxiv/urls.json').read_text())
    # Trozos que no pasaron comprobar_arxiv.py (casi todos, falsas alarmas de fórmulas): fuera.
    failed = set((ROOT / 'datos/arxiv/fallos-lotes-43-62.txt').read_text().split())
    for n in range(43, 100):
        lot, out = ROOT / ('datos/arxiv/lotes/lote_%02d.jsonl' % n), ROOT / ('datos/arxiv/salida/lote_%02d.jsonl' % n)
        if not out.exists():
            continue
        src = {r['id']: r for r in map(json.loads, lot.open())}
        for line in out.open():
            # GLM puede estar escribiendo el lote: una línea a medias se salta.
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get('id') in src and r.get('traduccion') and r['id'] not in failed:
                url = urls[r['id'][:5]]
                yield {'fuente': 'arxiv', 'tipo': src[r['id']]['tipo'], 'formato': 'texto', 'url': url, 'grupo': url,
                       'profesor': 'GLM 5.3 Flash', 'en': src[r['id']]['fuente'], 'es': r['traduccion']}


def main():
    exam = [json.loads(l) for l in (ROOT / 'datos/base/examen.jsonl').open()]
    banned_groups = {r['grupo'] for r in exam}
    banned_text = {r['en'].strip() for r in exam}
    pools = collections.defaultdict(list)
    dropped = collections.Counter()
    seen = set()
    for r in list(human()) + list(teacher()):
        if not r['en'].strip() or not r['es'].strip() or r['en'] == r['es']:
            dropped['vacío o igual'] += 1
        elif untranslated(r['en'], r['es']):
            dropped['sin traducir'] += 1
        elif r['grupo'] in banned_groups or r['en'].strip() in banned_text:
            dropped['está en el examen'] += 1
        elif r['en'].strip() in seen:
            dropped['repetido'] += 1
        else:
            seen.add(r['en'].strip())
            pools[r['fuente']].append(r)
    rng = random.Random(SEED)
    chosen = []
    print('%-18s %9s %9s' % ('fuente', 'hay', 'entran'))
    for fuente in sorted(pools):
        pool = pools[fuente]
        rng.shuffle(pool)
        take = pool[:CUPOS.get(fuente, len(pool))]
        chosen += take
        print('%-18s %9d %9d' % (fuente, len(pool), len(take)))
    print('%-18s %9d %9d' % ('total', sum(map(len, pools.values())), len(chosen)))
    print('descartados:', dict(dropped))
    print('por formato:', dict(collections.Counter(r['formato'] for r in chosen)))
    print('por profesor:', dict(collections.Counter(r.get('profesor', 'humano') for r in chosen)))
    if '--solo-contar' in sys.argv:
        return
    rng.shuffle(chosen)
    OUT.mkdir(exist_ok=True)
    with (OUT / 'entrenamiento.jsonl').open('w') as f:
        for i, r in enumerate(chosen, 1):
            f.write(json.dumps({'id': 'v%06d' % i, **r}, ensure_ascii=False) + '\n')
    print('escrito', OUT / 'entrenamiento.jsonl')


if __name__ == '__main__':
    main()
