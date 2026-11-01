#!/usr/bin/env python3
"""Traduce los dos exámenes con un modelo de llama-swap (ai-lab).

Usa el prompt corto del modelo base (prompt.py), como evaluar.py, o con
--profesor el de los rivales y profesores (colab/profesor.md). Escribe
resultados/profesores/NOMBRE/traducciones.json en el formato de
colab/profesor.py, para puntuarlo con puntuar_profesor.py y COMET.

Con EXAMEN=datos/examenes/externos.jsonl traduce los exámenes públicos de dominio.

Uso: .venv/bin/python scripts/traducir_examenes.py MODELO NOMBRE [--sin-razonar] [--temperatura T] [--hilos N] [--profesor]
"""
import argparse
import os
import concurrent.futures
import json
import pathlib
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from evaluar import URL, translate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('modelo')
    ap.add_argument('nombre')
    ap.add_argument('--sin-razonar', action='store_true')
    ap.add_argument('--temperatura', type=float, default=0.2)
    ap.add_argument('--profesor', action='store_true', help='prompt de colab/profesor.md, como los rivales')
    ap.add_argument('--hilos', type=int, default=1, help='peticiones a la vez; llama-swap corre con -np 1')
    args = ap.parse_args()
    exam = [json.loads(l) for l in (ROOT / os.environ.get('EXAMEN', 'datos/examenes/entrada.jsonl')).open()]

    system = (ROOT / 'colab/profesor.md').read_text()

    def teacher(r):
        body = {'model': args.modelo, 'temperature': args.temperatura, 'max_tokens': max(256, len(r['en'])), 'stream': False,
                'messages': [{'role': 'system', 'content': system},
                             {'role': 'user', 'content': 'Formato: %s\n\n%s' % (r['formato'], r['en'])}]}
        if args.sin_razonar:
            body['chat_template_kwargs'] = {'enable_thinking': False}
        req = urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=900) as resp:
            d = json.load(resp)
        return d['choices'][0]['message']['content'].strip(), d['choices'][0].get('finish_reason'), time.time() - t0

    def one(r):
        call = teacher if args.profesor else lambda x: translate(args.modelo, x['en'], args.temperatura, args.sin_razonar)
        out, fin, secs = call(r)
        return {'id': r['id'], 'salida': out, 'fin': fin, 'tokens': None, 'segundos': round(secs, 2)}

    t0 = time.time()
    rows = []
    with concurrent.futures.ThreadPoolExecutor(args.hilos) as pool:
        for i, row in enumerate(pool.map(one, exam), 1):
            rows.append(row)
            if i % 100 == 0:
                print('%d/%d' % (i, len(exam)), file=sys.stderr, flush=True)
    folder = ROOT / 'resultados/profesores' / args.nombre
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'traducciones.json').write_text(json.dumps(
        {'modelo': args.modelo, 'prompt': 'colab/profesor.md' if args.profesor else 'prompt.py', 'temperatura': args.temperatura, 'segundos': round(time.time() - t0), 'tokens': None, 'filas': rows},
        ensure_ascii=False, indent=1))
    print('listo en %d s' % (time.time() - t0))


if __name__ == '__main__':
    main()
