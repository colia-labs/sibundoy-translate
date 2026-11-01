#!/usr/bin/env python3
"""Prueba un modelo como profesor de traducción en una VM de Colab.

Instala vLLM, sirve el modelo y traduce los exámenes
(/content/examen.jsonl) con el prompt de profesor (/content/profesor.md),
con muchas peticiones a la vez. Escribe /content/salida/traducciones.json
y al final imprime LISTO.

Uso (en la VM): python3 -u profesor.py MODELO [argumentos extra de vllm serve]

/content/peticion.json se añade a cada petición; sirve para apagar el
razonamiento, que cada familia de modelos pide de una forma:
  Qwen y Gemma: {"chat_template_kwargs": {"enable_thinking": false}}
  gpt-oss:      {"reasoning_effort": "low"}
Con {"plantilla": "translategemma"} no se usa el prompt de profesor: el texto va
en la plantilla propia de TranslateGemma (inglés → español de México) y se
pide por /v1/completions.

Si existe /content/hf_token, se usa para bajar modelos con acceso restringido.
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 8000
URL = 'http://127.0.0.1:%d/v1/chat/completions' % PORT
WORKERS = 64


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


def translate(model, system, extra, row, tokenizer=None):
    if tokenizer is not None:
        prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': [
            {'type': 'text', 'source_lang_code': 'en', 'target_lang_code': 'es-MX', 'text': row['en']}]}],
            tokenize=False, add_generation_prompt=True)
        url = URL.replace('chat/completions', 'completions')
        body = {'model': model, 'temperature': 0.2, 'max_tokens': 4096, 'prompt': prompt}
    else:
        url = URL
        body = {'model': model, 'temperature': 0.2, 'max_tokens': 4096,
                'messages': [{'role': 'system', 'content': system},
                             {'role': 'user', 'content': 'Formato: %s\n\n%s' % (row['formato'], row['en'])}], **extra}
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    t0 = time.time()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.load(r)
            c = d['choices'][0]
            text = c['text'] if 'text' in c else c['message'].get('content')
            return {'id': row['id'], 'salida': (text or '').strip(), 'fin': c.get('finish_reason'),
                    'tokens': d.get('usage', {}).get('completion_tokens'), 'segundos': round(time.time() - t0, 2)}
        except urllib.error.HTTPError as e:
            err = '%s: %s' % (e, e.read().decode(errors='replace')[:500])
            time.sleep(5)
        except Exception as e:
            err = str(e)
            time.sleep(5)
    return {'id': row['id'], 'salida': '', 'fin': 'error: ' + err, 'tokens': 0, 'segundos': round(time.time() - t0, 2)}


def main():
    model, extra = sys.argv[1], sys.argv[2:]
    request = json.load(open('/content/peticion.json'))
    template = request.pop('plantilla', None)
    if os.path.exists('/content/hf_token'):
        os.environ['HF_TOKEN'] = open('/content/hf_token').read().strip()
    t0 = time.time()
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'vllm'], check=True)
    print('vllm instalado en %d s' % (time.time() - t0), flush=True)
    log = open('/content/vllm.txt', 'w')
    proc = subprocess.Popen(['vllm', 'serve', model, '--port', str(PORT), '--max-model-len', '8192',
                             '--gpu-memory-utilization', '0.92', '--max-num-seqs', str(WORKERS)] + extra,
                            stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'VLLM_LOGGING_LEVEL': 'WARNING'})
    print('modelo listo en %d s' % wait_ready(proc), flush=True)
    system = open('/content/profesor.md').read()
    exam = [json.loads(l) for l in open('/content/examen.jsonl')]
    tokenizer = None
    if template == 'translategemma':
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model)
    t1 = time.time()
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(lambda r: translate(model, system, request, r, tokenizer), exam))
    secs = time.time() - t1
    tokens = sum(r['tokens'] or 0 for r in rows)
    os.makedirs('/content/salida', exist_ok=True)
    json.dump({'modelo': model, 'peticion': request, 'extra': extra, 'segundos': round(secs), 'tokens': tokens, 'filas': rows},
              open('/content/salida/traducciones.json', 'w'), ensure_ascii=False, indent=1)
    print('%d traducciones en %d s, %d tokens (%.0f tokens/s)' % (len(rows), secs, tokens, tokens / secs), flush=True)
    proc.terminate()
    print('LISTO', flush=True)


if __name__ == '__main__':
    main()
