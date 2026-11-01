#!/usr/bin/env python3
"""Entrena el LoRA del modelo base en Colab y lo deja en GGUF.

Se ejecuta en la VM de Colab, en /content, con estos ficheros subidos antes:
entrenamiento.jsonl (datos/base) y prompt.py (scripts). Escribe en
/content/salida/: el adaptador LoRA, el registro de la pérdida y el GGUF en
Q4_K_M y Q8_0.

Versiones y configuración de LoRA: las del cuaderno oficial de SFT de Liquid
(Liquid4All/cookbook, lfm3_sft_with_trl.ipynb).

Uso en la VM: python3 entrenar.py [--pasos N] [--modelo M] [--epocas E] [--rango R] [--guardar-cada N]
  --pasos N         parar tras N pasos (prueba corta)
  --modelo M        modelo de partida (por defecto, el instruct LiquidAI/LFM3-1.7B)
  --guardar-cada N  guarda el LoRA y el estado del optimizador cada N pasos en
                    /content/checkpoints/; si ya hay alguno, sigue desde el último.

Sibundoy-Translate-1.7B se entrenó con:
  --modelo LiquidAI/LFM3-1.7B-Base --rango 64 --epocas 1 --guardar-cada 250
"""
import argparse
import json
import os
import pathlib
import random
import subprocess
import sys
import time

PACKAGES = ['torch==2.14.1', 'torchvision==0.29.1', 'torchao==0.18.0', 'trl==1.16.0', 'transformers==5.20.2',
            'peft==0.21.2', 'accelerate==1.15.0', 'datasets==5.1.0', 'huggingface-hub==2.3.0',
            'tokenizers==0.23.3', 'safetensors==0.8.0']
MODEL = 'LiquidAI/LFM3-1.7B'
WORK = pathlib.Path('/content')
OUT = WORK / 'salida'
SEED = 20261029
VALIDATION = 0.02
MAX_VALIDATION = 500


def sh(cmd, **kw):
    print('$ ' + cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True, **kw)


def load_examples(prompt):
    rows = [json.loads(l) for l in (WORK / 'entrenamiento.jsonl').open()]
    random.Random(SEED).shuffle(rows)
    examples = [{'prompt': [{'role': 'user', 'content': prompt.user_message(r['en'])}],
                 'completion': [{'role': 'assistant', 'content': r['es']}],
                 'chat_template_kwargs': {'enable_thinking': False}} for r in rows]
    n_val = min(MAX_VALIDATION, max(20, int(len(examples) * VALIDATION)))
    return examples[n_val:], examples[:n_val]


def train(max_steps, model_id, epochs, rank, save_every):
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback
    from trl import SFTConfig, SFTTrainer

    sys.path.insert(0, str(WORK))
    import prompt

    os.environ['WANDB_DISABLED'] = 'true'
    use_bf16 = torch.cuda.is_bf16_supported(including_emulation=False)
    dtype = torch.bfloat16 if use_bf16 else torch.float16
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, padding_side='left')
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, device_map='auto', trust_remote_code=True)
    train_rows, val_rows = load_examples(prompt)
    print('ejemplos: %d de entrenamiento, %d de validación' % (len(train_rows), len(val_rows)), flush=True)
    texts = [tokenizer.apply_chat_template(r['prompt'] + r['completion'], tokenize=False, enable_thinking=False)
             for r in train_rows]
    lengths = sorted(len(ids) for ids in tokenizer(texts, add_special_tokens=False)['input_ids'])
    print('tokens por ejemplo: mediana %d, p99 %d, máximo %d; %d de %d pasan de %d y se recortan' % (
        lengths[len(lengths) // 2], lengths[int(len(lengths) * 0.99)], lengths[-1],
        sum(n > 2048 for n in lengths), len(lengths), 2048), flush=True)
    sample = train_rows[0]
    print(tokenizer.apply_chat_template(sample['prompt'] + sample['completion'], tokenize=False, enable_thinking=False)[-600:], flush=True)

    peft_config = LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05, task_type='CAUSAL_LM',
                             target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'in_proj', 'out_proj', 'w1', 'w2', 'w3'])
    args = SFTConfig(
        output_dir=str(WORK / 'checkpoints'),
        num_train_epochs=epochs,
        max_steps=max_steps or -1,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=2,
        learning_rate=2e-4,
        lr_scheduler_type='cosine',
        warmup_steps=0.05,
        max_length=2048,
        logging_steps=10,
        eval_strategy='steps',
        eval_steps=save_every or 50,
        save_strategy='steps' if save_every else 'no',
        save_steps=save_every or 500,
        save_total_limit=2,
        bf16=use_bf16,
        fp16=not use_bf16,
        report_to='none',
        seed=SEED,
    )
    class Progress(TrainerCallback):
        """Deja el historial de pérdida en /content/progreso.json para seguirlo en vivo."""
        def on_train_begin(self, args, state, control, **kwargs):
            self.start, self.first_step = time.time(), state.global_step

        def on_log(self, args, state, control, **kwargs):
            (WORK / 'progreso.json').write_text(json.dumps(
                {'modelo': model_id, 'paso': state.global_step, 'pasos': state.max_steps, 'paso_inicio': self.first_step,
                 'segundos': time.time() - self.start, 'historial': state.log_history}))

    trainer = SFTTrainer(model=model, args=args, train_dataset=Dataset.from_list(train_rows),
                         eval_dataset=Dataset.from_list(val_rows), processing_class=tokenizer, peft_config=peft_config,
                         callbacks=[Progress()])
    trainer.model.print_trainable_parameters()
    checkpoints = sorted((WORK / 'checkpoints').glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[1]))
    if save_every and checkpoints:
        print('sigo desde %s' % checkpoints[-1].name, flush=True)
    trainer.train(resume_from_checkpoint=str(checkpoints[-1]) if save_every and checkpoints else None)
    print('memoria de GPU máxima: %.1f GB' % (torch.cuda.max_memory_reserved() / 1e9), flush=True)

    OUT.mkdir(exist_ok=True)
    (OUT / 'perdida.json').write_text(json.dumps(trainer.state.log_history, indent=1))
    samples(trainer.model, tokenizer, val_rows[:5])
    trainer.save_model(str(OUT / 'lora'))
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(str(WORK / 'fusionado'))
    tokenizer.save_pretrained(str(WORK / 'fusionado'))


def samples(model, tokenizer, rows):
    """Traduce unos ejemplos de validación: comprueba que responde solo con la traducción, sin razonar."""
    import torch
    model.eval()
    out = []
    for r in rows:
        text = tokenizer.apply_chat_template(r['prompt'], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = tokenizer(text, return_tensors='pt', add_special_tokens=False).to(model.device)
        with torch.no_grad():
            gen = model.generate(**ids, max_new_tokens=400, do_sample=False)
        answer = tokenizer.decode(gen[0][ids['input_ids'].shape[1]:], skip_special_tokens=True)
        out.append({'entrada': r['prompt'][0]['content'][-300:], 'salida': answer, 'referencia': r['completion'][0]['content']})
        print('MUESTRA:', answer[:300].replace('\n', ' '), flush=True)
    (OUT / 'muestras.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))


def to_gguf():
    if not (WORK / 'llama.cpp').exists():
        sh('git clone -q --depth 1 https://github.com/ggml-org/llama.cpp %s' % (WORK / 'llama.cpp'))
    # Solo gguf-py: sus requisitos completos bajan torch y transformers a versiones que no conocen LFM3.
    sh('pip install -q %s' % (WORK / 'llama.cpp/gguf-py'))
    sh('python3 %s %s --outtype bf16 --outfile %s' % (WORK / 'llama.cpp/convert_hf_to_gguf.py', WORK / 'fusionado', WORK / 'modelo-bf16.gguf'))
    # Solo la herramienta de cuantizar, sin CUDA: tarda un par de minutos.
    sh('cmake -S %s -B %s -DGGML_CUDA=OFF -DLLAMA_CURL=OFF > /dev/null' % (WORK / 'llama.cpp', WORK / 'llama.cpp/build'))
    sh('cmake --build %s --target llama-quantize -j > /dev/null' % (WORK / 'llama.cpp/build'))
    for kind in ('Q4_K_M', 'Q8_0'):
        sh('%s %s %s %s > /dev/null 2>&1' % (WORK / 'llama.cpp/build/bin/llama-quantize', WORK / 'modelo-bf16.gguf', OUT / ('modelo-%s.gguf' % kind), kind))
    sh('ls -la %s' % OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pasos', type=int, default=0, help='parar tras N pasos (prueba corta)')
    ap.add_argument('--modelo', default=MODEL)
    ap.add_argument('--epocas', type=float, default=2)
    ap.add_argument('--rango', type=int, default=16)
    ap.add_argument('--guardar-cada', type=int, default=0)
    ap.add_argument('--sin-gguf', action='store_true')
    ap.add_argument('--solo-gguf', action='store_true', help='convertir un /content/fusionado que ya existe')
    args = ap.parse_args()
    sh('pip install -q %s' % ' '.join('"%s"' % p for p in PACKAGES))
    if not args.solo_gguf:
        train(args.pasos, args.modelo, args.epocas, args.rango, args.guardar_cada)
    if not args.sin_gguf:
        to_gguf()
    print('LISTO', flush=True)


if __name__ == '__main__':
    main()
