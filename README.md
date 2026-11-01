# Sibundoy-Translate

**[English](#english) · [Español](#español)**

<a id="english"></a>

## English

The code we used to build [Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B), an English-to-Spanish translator from [ColIA](https://colia.org) that keeps HTML and Markdown intact: data collection, teacher translations, training, merging and evaluation.

| | |
|---|---|
| Model (safetensors) | [colia-labs/Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B) |
| GGUF files | [colia-labs/Sibundoy-Translate-1.7B-GGUF](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B-GGUF) |
| Launch post | [colia.org/blog/sibundoy-translate-1-7b](https://colia.org/blog/sibundoy-translate-1-7b/) |

The code, its comments and the teacher instructions are in Spanish. Results, data mix and limitations are in the model card.

### What is not here

**The training data.** We publish the code that builds it, not the data. The sources and their licenses are listed in the model card.

### How it was built

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

### Requirements

- Python 3.12 and `pip install -r requirements.txt` for the local scripts.
- The [Google Colab CLI](https://github.com/googlecolab/google-colab-cli) 0.7.5 (`colab`) for the scripts in `colab/`. They create a VM, upload the files, run the job and shut the VM down.

### License

The code is under the MIT license (see [LICENSE](LICENSE)). The model has its own license, the LFM Open License v1.0: see the [model card](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B).

### Contact

Questions and bugs in [Issues](https://github.com/colia-labs/sibundoy-translate/issues), or at hola@colia.org.

---

<a id="español"></a>

## Español

El código con el que hicimos [Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B), un traductor de inglés a español de [ColIA](https://colia.org) que conserva el HTML y el Markdown: la recogida de datos, las traducciones de los profesores, el entrenamiento, la fusión y la medición.

| | |
|---|---|
| Modelo (safetensors) | [colia-labs/Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B) |
| Archivos GGUF | [colia-labs/Sibundoy-Translate-1.7B-GGUF](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B-GGUF) |
| Post del lanzamiento | [colia.org/es/blog/sibundoy-translate-1-7b](https://colia.org/es/blog/sibundoy-translate-1-7b/) |

Los resultados, la mezcla de datos y lo que el modelo no hace bien están en la card del modelo.

### Qué no está aquí

**Los datos de entrenamiento.** Publicamos el código que los arma, no los datos. Las fuentes y sus licencias están en la card del modelo.

### Cómo se hizo

Todo se ejecuta desde la raíz del repo. Cada script explica al principio sus entradas, sus salidas y sus opciones.

| Paso | Scripts | Qué hace |
|---|---|---|
| 1. Fuentes humanas | `scripts/fuentes/` | Baja y alinea Global Voices, SciELO, Tatoeba, FineTranslations y la documentación de Python en español. Reúne Wikinews, PLOS y arXiv para los profesores |
| 2. Traducciones de los profesores | `scripts/preparar_cola.py`, `scripts/preparar_masivo.py`, `colab/lanzar_masivo.sh`, `colab/traducir_masivo.py`, `instrucciones/` | Gemma 4 31B traduce en Colab con vLLM. GLM 5.3 Flash traduce en sesiones de agente que siguen `instrucciones/cola.md` |
| 3. Comprobación y correcciones | `scripts/comprobador.py`, `scripts/comprobar_*.py`, `scripts/correcciones_masivo.py`, `scripts/revision.py` | Comprueba cifras, enlaces, etiquetas, fórmulas e idioma. Otro profesor reescribe las traducciones que fallan |
| 4. Mezcla de datos | `scripts/unificar.py`, `scripts/unificar_v2.py` | Junta todas las fuentes, pone un tope a cada una, quita lo que se parece a los exámenes y escribe el archivo de entrenamiento |
| 5. Entrenamiento | `colab/lanzar_entrenamiento.sh`, `colab/vigilar_entrenamiento.sh`, `colab/entrenar.py` | LoRA de rango 64 sobre LFM3-1.7B-Base, una vuelta a los datos en una L4 de Colab, con una copia cada 250 pasos |
| 6. Fusión | `scripts/fusionar.py` | Une el LoRA al modelo base en bf16 para publicarlo en Hugging Face |
| 7. Medición | `scripts/preparar_examenes.py`, `scripts/preparar_externos.py`, `scripts/traducir_examenes.py`, `scripts/puntuar_profesor.py`, `colab/comet.sh`, `scripts/rasgos_regionales.py`, `scripts/contar_repetidas.py` | Traduce los exámenes, calcula chrF, COMET y formato, cuenta los rasgos regionales y comprueba qué se repite con los datos de entrenamiento |
| 8. Gráficas | `scripts/graficas_card.py` | Las gráficas de la card del modelo |

La orden de entrenamiento del modelo publicado:

```sh
setsid nohup colab/lanzar_entrenamiento.sh base L4 datos/base-v2/entrenamiento.jsonl \
  --modelo LiquidAI/LFM3-1.7B-Base --rango 64 --epocas 1 --guardar-cada 250
```

La instrucción del modelo está en `scripts/prompt.py`, y es la misma al entrenar y al medir. La de los profesores está en `colab/profesor.md`.

Por dentro fue la segunda versión; la primera nunca se publicó. Por eso algunos scripts dicen «v2», y `unificar.py` es la mezcla de la primera versión, que la segunda reutiliza.

### Requisitos

- Python 3.12 y `pip install -r requirements.txt` para los scripts locales.
- El [CLI de Google Colab](https://github.com/googlecolab/google-colab-cli) 0.7.5 (`colab`) para los scripts de `colab/`. Crean una VM, suben los archivos, lanzan el trabajo y apagan la VM.

### Licencia

El código tiene licencia MIT (ver [LICENSE](LICENSE)). El modelo tiene su propia licencia, la LFM Open License v1.0: ver la [card del modelo](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B).

### Contacto

Preguntas y fallos en [Issues](https://github.com/colia-labs/sibundoy-translate/issues), o en hola@colia.org.
