#!/usr/bin/env python3
"""Mide un modelo de llama-swap con el examen público del modelo base.

Por cada par de datos/base/examen.jsonl pide la traducción con el prompt de
prompt.py y guarda el resultado. Al final da, en total, por fuente y por
formato:
- chrF frente a la traducción humana (sacrebleu);
- formato conservado: en HTML, los mismos enlaces y el mismo número de
  cursivas y negritas; en Markdown, las mismas URL; en texto, sin etiquetas;
- textos con rasgos del español de España.

Uso: .venv/bin/python scripts/evaluar.py MODELO [--sin-razonar] [--temperatura T]
"""
import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

import sacrebleu

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / 'fuentes'))
import html_simple  # noqa: E402
import prompt  # noqa: E402
from rasgos import spain_hits  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = os.environ.get('LLAMA_URL', 'http://localhost:8080/v1/chat/completions')
MD_LINK = re.compile(r'\]\(([^)\s]+)\)')


def translate(model, text, temperature, no_think):
    body = {'model': model, 'messages': [{'role': 'user', 'content': prompt.user_message(text)}],
            'temperature': temperature, 'max_tokens': max(256, len(text)), 'stream': False}
    if no_think:
        body['chat_template_kwargs'] = {'enable_thinking': False}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    return d['choices'][0]['message']['content'].strip(), d['choices'][0].get('finish_reason'), time.time() - t0


def format_ok(r, out):
    if r['formato'] == 'html':
        return html_simple.signature(html_simple.simplify(out)) == html_simple.signature(r['en'])
    if r['formato'] == 'markdown':
        return MD_LINK.findall(out) == MD_LINK.findall(r['en'])
    return '<' not in out or '<' in r['en']


def summary(rows):
    def block(sel):
        if not sel:
            return None
        return {'n': len(sel),
                'chrf': round(sacrebleu.corpus_chrf([x['salida'] for x in sel], [[x['es'] for x in sel]]).score, 2),
                'formato_ok': sum(x['formato_ok'] for x in sel),
                'rasgos_espana': sum(x['rasgos_espana'] for x in sel),
                'cortadas': sum(x['fin'] == 'length' for x in sel)}
    out = {'total': block(rows)}
    for key in ('fuente', 'formato'):
        for v in sorted({x[key] for x in rows}):
            out['%s=%s' % (key, v)] = block([x for x in rows if x[key] == v])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('modelo')
    ap.add_argument('--sin-razonar', action='store_true', help='envía enable_thinking: false (LFM3)')
    ap.add_argument('--temperatura', type=float, default=0.2)
    args = ap.parse_args()
    exam = [json.loads(l) for l in (ROOT / 'datos/base/examen.jsonl').open()]
    rows = []
    t0 = time.time()
    for i, r in enumerate(exam, 1):
        out, fin, secs = translate(args.modelo, r['en'], args.temperatura, args.sin_razonar)
        rows.append({**r, 'salida': out, 'fin': fin, 'segundos': round(secs, 2),
                     'formato_ok': format_ok(r, out), 'rasgos_espana': bool(spain_hits(out))})
        if i % 25 == 0:
            print('%d/%d' % (i, len(exam)), file=sys.stderr)
    res = {'modelo': args.modelo, 'sin_razonar': args.sin_razonar, 'temperatura': args.temperatura,
           'fecha': dt.datetime.now().isoformat(timespec='seconds'), 'segundos_total': round(time.time() - t0),
           'prompt': prompt.INSTRUCTION, 'resumen': summary(rows), 'filas': rows}
    dest = ROOT / 'resultados' / ('examen-%s-%s.json' % (args.modelo, dt.datetime.now().strftime('%Y%m%d-%H%M')))
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for k, v in res['resumen'].items():
        print('%-28s %s' % (k, v))
    print('Resultados en', dest)


if __name__ == '__main__':
    main()
