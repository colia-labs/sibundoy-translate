#!/usr/bin/env python3
"""Traduce en masa con un profesor servido por vLLM en una VM de Colab.

Lee /content/entrada.jsonl (de scripts/preparar_masivo.py). Cada unidad (una
noticia, o un título con su resumen) va en una sola petición con los trozos
numerados [[1]], [[2]]…, para que el profesor use los mismos términos en todo
el texto. Si la respuesta no trae exactamente esos números, la unidad se
repite trozo a trozo.

Añade cada unidad terminada a /content/salida/resultado.jsonl:
{"uid", "modo": "unidad" o "trozos", "trozos": [{"id", "traduccion", "fin"}]}.
Se puede relanzar: salta las unidades que ya están. Al final imprime LISTO.

Uso (en la VM): python3 -u traducir_masivo.py MODELO [argumentos extra de vllm serve]
/content/peticion.json se añade a cada petición (ver profesor.py).
"""
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

PORT = 8000
URL = 'http://127.0.0.1:%d/v1/chat/completions' % PORT
WORKERS = 256
OUT = '/content/salida/resultado.jsonl'
MARK = re.compile(r'\[\[(\d+)\]\]')
ORIGIN = {
    'wikinews': 'Source: a Wikinews news article. Journalistic register, like a Spanish-language news agency. '
                'Quotes are translated too; use the same kind of quotation marks throughout the article.',
    'arxiv': 'Source: an arXiv abstract. Academic register. Keep in English the terms Spanish speakers use in English '
             '(prompt, benchmark, token, transformer), without quotes or italics. Copy LaTeX exactly.',
    'plos': 'Source: a PLOS article (biology, medicine or social sciences). Scientific register; if the summary is '
            'written for the general public, keep that clear and simple tone.',
}


def wait_ready(proc, limit=3600):
    t0 = time.time()
    while time.time() - t0 < limit:
        if proc.poll() is not None:
            raise SystemExit('vLLM terminó antes de estar listo (código %s)' % proc.returncode)
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/health' % PORT, timeout=5)
            return time.time() - t0
        except Exception:
            time.sleep(10)
    raise SystemExit('vLLM no arrancó en %d s' % limit)


def ask(model, system, extra, user, max_tokens):
    body = {'model': model, 'temperature': 0.2, 'max_tokens': max_tokens,
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], **extra}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    err = ''
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                d = json.load(r)
            c = d['choices'][0]
            return (c['message'].get('content') or '').strip(), c.get('finish_reason'), d.get('usage', {}).get('completion_tokens', 0)
        except urllib.error.HTTPError as e:
            err = '%s: %s' % (e, e.read().decode(errors='replace')[:300])
        except Exception as e:
            err = str(e)
        time.sleep(5)
    return '', 'error: ' + err, 0


def budget(text):
    # Unos 4 caracteres por token en inglés; el español sale algo más largo.
    return min(12000, 512 + len(text) // 2)


def whole(model, system, extra, u):
    # El prompt de sistema espera que el mensaje empiece por «Formato:».
    parts = ['Formato: %s' % u['trozos'][-1]['formato'], '', ORIGIN[u['origen']],
             'Translate each numbered segment. Reply with the same markers, each followed by its translation, '
             'in the same order and nothing else. Segment [[1]] is the title (plain text).', '']
    for n, t in enumerate(u['trozos'], 1):
        parts.append('[[%d]] %s' % (n, t['fuente']))
    user = '\n'.join(parts)
    text, fin, tokens = ask(model, system, extra, user, budget(user) * 2)
    found = MARK.split(text)
    # split da ['', '1', 'texto', '2', 'texto'…]
    numbers = [int(x) for x in found[1::2]]
    if fin != 'stop' or numbers != list(range(1, len(u['trozos']) + 1)):
        return None, tokens
    return [{'id': t['id'], 'traduccion': s.strip(), 'fin': fin} for t, s in zip(u['trozos'], found[2::2])], tokens


def piecewise(model, system, extra, u):
    out, total = [], 0
    for t in u['trozos']:
        user = 'Formato: %s\n\n%s' % (t['formato'], t['fuente'])
        text, fin, tokens = ask(model, system + '\n\n' + ORIGIN[u['origen']], extra, user, budget(t['fuente']) * 2)
        out.append({'id': t['id'], 'traduccion': text, 'fin': fin})
        total += tokens
    return out, total


def main():
    model, extra_args = sys.argv[1], sys.argv[2:]
    request = json.load(open('/content/peticion.json'))
    system = open('/content/profesor.md').read()
    t0 = time.time()
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'vllm'], check=True)
    print('vllm instalado en %d s' % (time.time() - t0), flush=True)
    log = open('/content/vllm.txt', 'w')
    proc = subprocess.Popen(['vllm', 'serve', model, '--port', str(PORT), '--max-model-len', '16384',
                             '--gpu-memory-utilization', '0.92', '--max-num-seqs', str(WORKERS),
                             '--enable-prefix-caching'] + extra_args,
                            stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'VLLM_LOGGING_LEVEL': 'WARNING'})
    print('modelo listo en %d s' % wait_ready(proc), flush=True)

    os.makedirs('/content/salida', exist_ok=True)
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)['uid'] for l in open(OUT)}
    todo = [u for u in map(json.loads, open('/content/entrada.jsonl')) if u['uid'] not in done]
    lock = threading.Lock()
    stats = {'unidades': 0, 'trozos_modo': 0, 'tokens': 0}
    t1 = time.time()

    def one(u):
        rows, tokens = whole(model, system, request, u)
        mode = 'unidad'
        if rows is None:
            rows, more = piecewise(model, system, request, u)
            tokens += more
            mode = 'trozos'
        with lock:
            with open(OUT, 'a') as f:
                f.write(json.dumps({'uid': u['uid'], 'modo': mode, 'trozos': rows}, ensure_ascii=False) + '\n')
            stats['unidades'] += 1
            stats['trozos_modo'] += mode == 'trozos'
            stats['tokens'] += tokens
            if stats['unidades'] % 200 == 0 or stats['unidades'] == len(todo):
                secs = time.time() - t1
                print('%d/%d unidades, %d repetidas trozo a trozo, %.0f tokens/s, faltan ~%.0f min' % (
                    stats['unidades'], len(todo), stats['trozos_modo'], stats['tokens'] / secs,
                    secs / stats['unidades'] * (len(todo) - stats['unidades']) / 60), flush=True)

    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(one, todo))
    proc.terminate()
    print('LISTO', flush=True)


if __name__ == '__main__':
    main()
