#!/usr/bin/env python3
"""Calcula COMET (Unbabel/wmt22-comet-da, Apache 2.0) en una VM de Colab.

Lee los exámenes de /content/entrada.jsonl y las traducciones de cada
modelo de /content/sistema-NOMBRE.json (formato de colab/profesor.py).
Escribe /content/comet-NOMBRE.json con la nota de cada frase, de 0 a 1,
y al final imprime LISTO.

Uso (en la VM), con unbabel-comet instalado en un entorno aparte (ver comet.sh):
  /content/cv/bin/python -u puntuar_comet.py
"""
import json
import pathlib

import torch
from comet import download_model, load_from_checkpoint


def main():
    exam = {r['id']: r for r in map(json.loads, open('/content/entrada.jsonl'))}
    model = load_from_checkpoint(download_model('Unbabel/wmt22-comet-da'))
    for path in sorted(pathlib.Path('/content').glob('sistema-*.json')):
        rows = [t for t in json.load(path.open())['filas'] if t['id'] in exam]
        data = [{'src': exam[t['id']]['en'], 'mt': t['salida'], 'ref': exam[t['id']]['es']} for t in rows]
        scores = model.predict(data, batch_size=64, gpus=1 if torch.cuda.is_available() else 0, progress_bar=False).scores
        json.dump({t['id']: s for t, s in zip(rows, scores)}, open('/content/comet-%s.json' % path.stem[len('sistema-'):], 'w'))
        print('%s: %d frases, media %.4f' % (path.stem[len('sistema-'):], len(scores), sum(scores) / len(scores)), flush=True)
    print('LISTO', flush=True)


if __name__ == '__main__':
    main()
