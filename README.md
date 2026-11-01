# Sibundoy-Translate

**English** · [Español](README.es.md)

The code we used to build [Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B), an English-to-Spanish translator from [ColIA](https://colia.org) that keeps HTML and Markdown intact: data collection, teacher translations, training, merging and evaluation.

| | |
|---|---|
| Model (safetensors) | [colia-labs/Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B) |
| GGUF files | [colia-labs/Sibundoy-Translate-1.7B-GGUF](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B-GGUF) |
| Launch post | [colia.org/blog/sibundoy-translate-1-7b](https://colia.org/blog/sibundoy-translate-1-7b/) |

The code, its comments and the teacher instructions are in Spanish. Results, data mix and limitations are in the model card.

## What is not here

**The training data.** We publish the code that builds it, not the data. The sources and their licenses are listed in the model card.

## How it was built

Run everything from the repo root. Each script explains its inputs, outputs and options at the top.

| Step | Scripts | What it does |
|---|---|---|
| 1. Human sources | `scripts/fuentes/` | Downloads and aligns Global Voices, SciELO, Tatoeba, FineTranslations and the Spanish Python docs. Collects Wikinews, PLOS and arXiv for the teachers |
| 2. Teacher translations | `scripts/preparar_cola.py`, `scripts/preparar_masivo.py`, `colab/lanzar_masivo.sh`, `colab/traducir_masivo.py`, `instrucciones/` | Gemma 4 31B translates on Colab with vLLM. GLM 5.3 Flash translates in agent sessions that follow `instrucciones/cola.md` |
| 3. Checks and fixes | `scripts/comprobador.py`, `scripts/comprobar_*.py`, `scripts/correcciones_masivo.py`, `scripts/revision.py` | Checks numbers, links, tags, formulas and language. Another teacher rewrites the translations that fail |
| 4. Data mix | `scripts/unificar.py`, `scripts/unificar_v2.py` | Joins all sources, caps each one, removes anything close to the tests and writes the training file |
| 5. Training | `colab/lanzar_entrenamiento.sh`, `colab/vigilar_entrenamiento.sh`, `colab/entrenar.py` | Rank-64 LoRA on LFM3-1.7B-Base, one epoch on a Colab L4, with a copy every 250 steps |
| 6. Merge | `scripts/fusionar.py` | Merges the LoRA into the base model in bf16 for the Hugging Face release |
| 7. Evaluation | `scripts/preparar_examenes.py`, `scripts/preparar_externos.py`, `scripts/traducir_examenes.py`, `scripts/puntuar_profesor.py`, `colab/comet.sh`, `scripts/rasgos_regionales.py`, `scripts/contar_repetidas.py` | Translates the tests, scores chrF, COMET and format, counts regional Spanish and checks overlap with the training data |
| 8. Charts | `scripts/graficas_card.py` | The charts of the model card |

The training command for the published model:

```sh
setsid nohup colab/lanzar_entrenamiento.sh base L4 datos/base-v2/entrenamiento.jsonl \
  --modelo LiquidAI/LFM3-1.7B-Base --rango 64 --epocas 1 --guardar-cada 250
```

The prompt is in `scripts/prompt.py`. It is the same for training and evaluation. The teacher prompt is in `colab/profesor.md`.

Internally this was the second version; the first one was never published. That is why some scripts say "v2", and `unificar.py` is the first version's data mix, which the second one reuses.

## Requirements

- Python 3.12 and `pip install -r requirements.txt` for the local scripts.
- The [Google Colab CLI](https://github.com/googlecolab/google-colab-cli) 0.7.5 (`colab`) for the scripts in `colab/`. They create a VM, upload the files, run the job and shut the VM down.

## License

The code is under the MIT license (see [LICENSE](LICENSE)). The model has its own license, the LFM Open License v1.0: see the [model card](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B).

## Contact

Questions and bugs in [Issues](https://github.com/colia-labs/sibundoy-translate/issues), or at hola@colia.org.
