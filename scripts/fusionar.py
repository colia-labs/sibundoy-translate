"""Fusiona el LoRA de la v2 base con LFM3-1.7B-Base, como colab/entrenar.py (bf16, merge_and_unload)."""
import json, sys, torch
from huggingface_hub import HfApi
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = 'LiquidAI/LFM3-1.7B-Base'
lora, out = sys.argv[1], sys.argv[2]
rev = HfApi().model_info(BASE).sha
print('base', BASE, rev, flush=True)
model = AutoModelForCausalLM.from_pretrained(BASE, revision=rev, dtype=torch.bfloat16, trust_remote_code=True)
model = PeftModel.from_pretrained(model, lora).merge_and_unload()
model.save_pretrained(out, safe_serialization=True)
AutoTokenizer.from_pretrained(lora, trust_remote_code=True).save_pretrained(out)
json.dump({'base': BASE, 'revision': rev}, open(out + '/fusion.json', 'w'))
print('LISTO', flush=True)
