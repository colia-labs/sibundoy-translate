# Sibundoy-Translate

[English](README.md) · **Español**

El código con el que hicimos [Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B), un traductor de inglés a español de [ColIA](https://colia.org) que conserva el HTML y el Markdown: la recogida de datos, las traducciones de los profesores, el entrenamiento, la fusión y la medición.

| | |
|---|---|
| Modelo (safetensors) | [colia-labs/Sibundoy-Translate-1.7B](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B) |
| Archivos GGUF | [colia-labs/Sibundoy-Translate-1.7B-GGUF](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B-GGUF) |
| Post del lanzamiento | [colia.org/es/blog/sibundoy-translate-1-7b](https://colia.org/es/blog/sibundoy-translate-1-7b/) |

Los resultados, la mezcla de datos y lo que el modelo no hace bien están en la card del modelo.

## Qué no está aquí

**Los datos de entrenamiento.** Publicamos el código que los arma, no los datos. Las fuentes y sus licencias están en la card del modelo.

## Cómo se hizo

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

## Requisitos

- Python 3.12 y `pip install -r requirements.txt` para los scripts locales.
- El [CLI de Google Colab](https://github.com/googlecolab/google-colab-cli) 0.7.5 (`colab`) para los scripts de `colab/`. Crean una VM, suben los archivos, lanzan el trabajo y apagan la VM.

## Licencia

El código tiene licencia MIT (ver [LICENSE](LICENSE)). El modelo tiene su propia licencia, la LFM Open License v1.0: ver la [card del modelo](https://huggingface.co/colia-labs/Sibundoy-Translate-1.7B).

## Contacto

Preguntas y fallos en [Issues](https://github.com/colia-labs/sibundoy-translate/issues), o en hola@colia.org.
