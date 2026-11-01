#!/usr/bin/env python3
"""Arma la cola de lotes para los profesores, mezclando todas las fuentes.

Cada lote junta unidades (una noticia, o un título con su resumen) de varias
fuentes y áreas, sacadas al azar con los pesos de WEIGHTS, hasta unas
WORDS palabras. Así, se corte donde se corte, lo traducido queda equilibrado.
Cuando un área se acaba, su peso se reparte entre las demás.

Los lotes se reparten por turno entre SESSIONS carpetas, una por sesión de
OpenCode: datos/cola/1/, 2/ y 3/, cada una con lotes/ y salida/. Las sesiones
traducen en paralelo sin pisarse.

Se puede volver a correr para añadir lotes: los que ya existen no se tocan y
sus unidades no se repiten. datos/cola/unidades.json guarda la URL, la fuente
y el área de cada unidad.

Uso: python3 scripts/preparar_cola.py [lotes_nuevos]
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/fuentes'))
import html_simple  # noqa: E402

COLA = ROOT / 'datos/cola'
SESSIONS = 3
WORDS = 2500
SEED = 20261030
SHARE_HTML, SHARE_MARKDOWN = 0.45, 0.30
# Noticias: lo que más falta. Las áreas de PLOS ONE se reparten su peso a partes iguales.
WEIGHTS = {'noticias': 0.35, 'arxiv': 0.15, 'plos-divulgacion': 0.10, 'plos-areas': 0.40}


def read(path):
    return [json.loads(l) for l in (ROOT / path).open()]


def units():
    """Todas las unidades posibles: {'uid', 'grupo', 'url', 'fuente', 'area', 'trozos'}."""
    out = []
    for k, r in enumerate(read('datos/fuentes/wikinews.jsonl'), 1):
        out.append({'uid': 'w%05d' % k, 'grupo': 'noticias', 'url': r['url'], 'fuente': 'wikinews', 'area': 'noticias',
                    'titulo': r['titulo'], 'parrafos': r['parrafos']})
    # arXiv: los 600 artículos nuevos (datos/arxiv/lotes-cola/), con sus ids y URLs ya asignados.
    urls = json.loads((ROOT / 'datos/arxiv/urls.json').read_text())
    area = {r['url']: r['area'] for r in read('datos/fuentes/arxiv-crudo-v2.jsonl')}
    by_id = {}
    for n in range(23, 43):
        for r in read('datos/arxiv/lotes-cola/lote_%02d.jsonl' % n):
            by_id.setdefault(r['id'][:5], {})[r['tipo']] = r['fuente']
    for aid, parts in sorted(by_id.items()):
        out.append({'uid': aid, 'grupo': 'arxiv', 'url': urls[aid], 'fuente': 'arxiv', 'area': area[urls[aid]],
                    'titulo': parts['titulo'], 'resumen': parts['resumen']})
    for k, r in enumerate(read('datos/fuentes/plos.jsonl'), 1):
        out.append({'uid': 'p%05d' % k, 'grupo': 'plos-divulgacion', 'url': r['url'], 'fuente': 'plos', 'area': r['revista'],
                    'titulo': r['titulo'], 'resumen': r['resumen']})
    for k, r in enumerate(read('datos/fuentes/plos-areas.jsonl'), 1):
        out.append({'uid': 'q%05d' % k, 'grupo': 'plos-areas', 'url': r['url'], 'fuente': 'plos-one', 'area': r['area'],
                    'titulo': r['titulo'], 'resumen': r['resumen']})
    return out


def lines(u, rng):
    if u['fuente'] == 'wikinews':
        roll = rng.random()
        fmt = 'html' if roll < SHARE_HTML else 'markdown' if roll < SHARE_HTML + SHARE_MARKDOWN else 'texto'
        yield {'id': u['uid'] + '-t', 'origen': 'wikinews', 'tipo': 'titulo', 'formato': 'texto', 'fuente': u['titulo']}
        for n, p in enumerate(u['parrafos'], 1):
            text = p if fmt == 'html' else html_simple.to_markdown(p) if fmt == 'markdown' else html_simple.to_text(p)
            yield {'id': '%s-p%02d' % (u['uid'], n), 'origen': 'wikinews', 'tipo': 'parrafo', 'formato': fmt, 'fuente': text}
    else:
        origen = 'arxiv' if u['fuente'] == 'arxiv' else 'plos'
        yield {'id': u['uid'] + '-t', 'origen': origen, 'tipo': 'titulo', 'formato': 'texto', 'fuente': u['titulo']}
        yield {'id': u['uid'] + '-r', 'origen': origen, 'tipo': 'resumen', 'formato': 'texto', 'fuente': u['resumen']}


def words(u):
    return len(u['titulo'].split()) + sum(len(html_simple.to_text(p).split()) for p in u.get('parrafos', [u.get('resumen', '')]))


def main():
    new = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    index_path = COLA / 'unidades.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    existing = sorted(COLA.glob('*/lotes/lote_*.jsonl'))
    rng = random.Random('%d-%d' % (SEED, len(existing)))
    pools = {}
    for u in units():
        if u['uid'] not in index:
            key = u['grupo'] if u['grupo'] != 'plos-areas' else 'plos-areas/' + u['area']
            pools.setdefault(key, []).append(u)
    for pool in pools.values():
        rng.shuffle(pool)
    n_areas = sum(k.startswith('plos-areas/') for k in pools)

    def weight(key):
        return WEIGHTS['plos-areas'] / n_areas if key.startswith('plos-areas/') else WEIGHTS[key]

    for s in range(1, SESSIONS + 1):
        (COLA / str(s) / 'lotes').mkdir(parents=True, exist_ok=True)
        (COLA / str(s) / 'salida').mkdir(exist_ok=True)
    made = 0
    for k in range(len(existing), len(existing) + new):
        session = k % SESSIONS + 1
        number = k // SESSIONS + 1
        chosen, total = [], 0
        while total < WORDS and any(pools.values()):
            keys = [key for key in pools if pools[key]]
            key = rng.choices(keys, [weight(x) for x in keys])[0]
            u = pools[key].pop()
            chosen.append(u)
            total += words(u)
        if not chosen:
            break
        with (COLA / str(session) / 'lotes' / ('lote_%04d.jsonl' % number)).open('w') as f:
            for u in chosen:
                index[u['uid']] = {'url': u['url'], 'fuente': u['fuente'], 'area': u['area'], 'sesion': session, 'lote': number}
                for line in lines(u, rng):
                    f.write(json.dumps(line, ensure_ascii=False) + '\n')
        made += 1
    index_path.write_text(json.dumps(index, indent=1, ensure_ascii=False))
    left = sum(len(p) for p in pools.values())
    print('%d lotes nuevos (%d en total); quedan %d unidades sin asignar' % (made, len(existing) + made, left))


if __name__ == '__main__':
    main()
