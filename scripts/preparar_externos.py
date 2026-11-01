#!/usr/bin/env python3
"""Reúne los exámenes públicos de dominio en datos/examenes/externos.jsonl.

Mismo formato que datos/examenes/entrada.jsonl (id, examen, fuente, formato,
en, es), para traducirlos y puntuarlos con los mismos scripts
(EXAMEN=datos/examenes/externos.jsonl).

- biomedico: WMT21 Biomedical, Medline en→es. Las frases del inglés y del
  español no casan una a una, así que cada resumen es un ítem (100).
- tico19: TICO-19 test, salud y COVID, referencia en español latinoamericano.
- ntrex: NTREX-128 (newstest2019), noticias, referencia en español de México.
- flores: FLORES+ devtest, si está bajado (repositorio con acceso restringido).

Los ficheros de origen están en datos/examenes/externos/<examen>/.
"""
import collections
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'datos/examenes/externos'


def biomedico():
    def docs(path):
        out = collections.defaultdict(list)
        for line in path.open():
            doc, _, text = line.rstrip('\n').split('\t', 2)
            out[doc].append(text.strip())
        return out
    en, es = docs(SRC / 'biomedico/medline_en2es_en.txt'), docs(SRC / 'biomedico/medline_en2es_es.txt')
    for doc in sorted(set(en) & set(es), key=lambda d: int(d[3:])):
        yield {'id': 'bio-%s' % doc, 'examen': 'biomedico', 'fuente': 'medline', 'formato': 'texto',
               'en': ' '.join(en[doc]), 'es': ' '.join(es[doc])}


def tico19():
    with (SRC / 'tico19/test.en-es-LA.tsv').open() as f:
        for i, r in enumerate(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)):
            yield {'id': 'tico-%04d' % i, 'examen': 'tico19', 'fuente': r['stringID'].split('_')[0].split(':')[0],
                   'formato': 'texto', 'en': r['sourceString'].strip(), 'es': r['targetString'].strip()}


def ntrex():
    en = (SRC / 'ntrex/newstest2019-src.eng.txt').read_text().splitlines()
    es = (SRC / 'ntrex/newstest2019-ref.spa-MX.txt').read_text().splitlines()
    assert len(en) == len(es)
    for i, (a, b) in enumerate(zip(en, es)):
        yield {'id': 'ntrex-%04d' % i, 'examen': 'ntrex', 'fuente': 'newstest2019', 'formato': 'texto', 'en': a.strip(), 'es': b.strip()}


def flores():
    en, es = SRC / 'flores/eng_Latn.jsonl', SRC / 'flores/spa_Latn.jsonl'
    if not en.exists():
        print('FLORES+ no está bajado: lo salto')
        return
    a = {r['id']: r for r in map(json.loads, en.open())}
    b = {r['id']: r for r in map(json.loads, es.open())}
    for k in sorted(set(a) & set(b)):
        yield {'id': 'flores-%04d' % k, 'examen': 'flores', 'fuente': a[k].get('domain', 'wiki'), 'formato': 'texto',
               'en': a[k]['text'].strip(), 'es': b[k]['text'].strip()}


def main():
    rows = [r for gen in (biomedico, tico19, ntrex, flores) for r in gen() if r['en'] and r['es']]
    with (ROOT / 'datos/examenes/externos.jsonl').open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(collections.Counter(r['examen'] for r in rows))


if __name__ == '__main__':
    main()
