#!/usr/bin/env python3
"""Pares de frases inglés → español de Tatoeba (CC BY 2.0 FR).

Lee las exportaciones oficiales por idioma (datos/crudo/tatoeba/) y elige
frases de al menos MIN_WORDS palabras, sin rasgos del español de España, con
una sola traducción por frase inglesa.

Uso: python3 tatoeba.py carpeta_crudo salida.jsonl [pares]
"""
import bz2
import json
import random
import sys

from rasgos import spain_hits

MIN_WORDS = 6
SEED = 20261029


def sentences(path):
    out = {}
    with bz2.open(path, 'rt') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 3:
                out[parts[0]] = parts[2]
    return out


def main():
    folder, out = sys.argv[1], sys.argv[2]
    want = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    eng = sentences(folder + '/eng_sentences.tsv.bz2')
    spa = sentences(folder + '/spa_sentences.tsv.bz2')
    pairs = {}
    with bz2.open(folder + '/eng-spa_links.tsv.bz2', 'rt') as f:
        for line in f:
            a, b = line.split()[:2]
            if a in eng and b in spa and a not in pairs:
                en, es = eng[a], spa[b]
                if len(en.split()) >= MIN_WORDS and not spain_hits(es):
                    pairs[a] = (b, en, es)
    rng = random.Random(SEED)
    chosen = rng.sample(sorted(pairs.items()), min(want, len(pairs)))
    with open(out, 'w') as f:
        for i, (a, (b, en, es)) in enumerate(chosen, 1):
            f.write(json.dumps({'id': 'tt-%04d' % i, 'fuente': 'tatoeba', 'url': 'https://tatoeba.org/es/sentences/show/%s' % a,
                                'en': en, 'es': es}, ensure_ascii=False) + '\n')
    print('%d pares de %d candidatos' % (len(chosen), len(pairs)), file=sys.stderr)


if __name__ == '__main__':
    main()
