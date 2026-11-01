#!/usr/bin/env python3
"""Pares inglés → español del Global Voices antiguo (hasta 2018) alineado por OPUS.

Es el mismo contenido CC BY 3.0 que globalvoices.py, ya emparejado frase a
frase por OPUS (versión v2018q4, formato Moses). El alineado es automático,
así que cada par pasa filtros: los dos lados en su idioma, longitudes
parecidas, las mismas cifras y sin rasgos del español de España.

Las frases van en el orden de los artículos. Para que haya textos del largo
de un párrafo, se juntan de 1 a MAX_JOIN frases seguidas que pasen todas los
filtros. Juntar frases de dos artículos distintos da un texto raro, pero la
traducción sigue siendo correcta.

Uso: python3 opus_gv.py carpeta_crudo salida.jsonl [pares]
"""
import json
import random
import re
import sys

from rasgos import spain_hits

MAX_JOIN = 4
MIN_WORDS = 4
MAX_CHARS = 1200
SEED = 20261030
URL = 'https://opus.nlpl.eu/GlobalVoices/v2018q4'
EN_WORDS = set('the and of to is that with for are was this have from they not'.split())
ES_WORDS = set('el la los las que de y en es por con para una del se no'.split())
DIGITS = re.compile(r'\d+')


def looks(text, mine, other):
    words = re.findall(r'[a-záéíóúñü]+', text.lower())
    a = sum(w in mine for w in words)
    return a > sum(w in other for w in words) and a >= 1


def clean(text):
    text = re.sub(r' · Global Voices$', '', text.strip())
    text = re.sub(r' ([;:,.!?)])', r'\1', text)
    return re.sub(r'\s+', ' ', text)


def good(en, es):
    if not en or not es or en == es or len(en) > MAX_CHARS or len(en.split()) < MIN_WORDS:
        return False
    if 'http' in en or not looks(en, EN_WORDS, ES_WORDS) or not looks(es, ES_WORDS, EN_WORDS):
        return False
    ratio = len(es) / len(en)
    if not 0.8 <= ratio <= 1.7:
        return False
    return sorted(DIGITS.findall(en)) == sorted(DIGITS.findall(es)) and not spain_hits(es)


def main():
    folder, out = sys.argv[1], sys.argv[2]
    want = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
    with open(folder + '/GlobalVoices.en-es.en') as f_en, open(folder + '/GlobalVoices.en-es.es') as f_es:
        lines = [(clean(a), clean(b)) for a, b in zip(f_en, f_es)]
    rng = random.Random(SEED)
    units, run, seen = [], [], set()
    for en, es in lines + [('', '')]:
        if good(en, es) and en not in seen:
            seen.add(en)
            run.append((en, es))
            continue
        # Un tramo de frases buenas seguidas se corta en trozos de 1 a MAX_JOIN.
        while run:
            n = rng.randint(1, MAX_JOIN)
            part, run = run[:n], run[n:]
            units.append((' '.join(p[0] for p in part), ' '.join(p[1] for p in part), len(part)))
    units = [u for u in units if len(u[0]) <= MAX_CHARS]
    chosen = rng.sample(units, min(want, len(units)))
    with open(out, 'w') as f:
        for i, (en, es, n) in enumerate(chosen, 1):
            f.write(json.dumps({'id': 'og-%05d' % i, 'fuente': 'opus-globalvoices', 'frases': n, 'url': URL,
                                'en': en, 'es': es}, ensure_ascii=False) + '\n')
    print('%d unidades de %d (de %d frases)' % (len(chosen), len(units), len(lines)), file=sys.stderr)


if __name__ == '__main__':
    main()
