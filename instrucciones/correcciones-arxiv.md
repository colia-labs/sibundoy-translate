# Instrucciones: corregir traducciones de arXiv

Un revisor marcó algunas traducciones de títulos y resúmenes de arXiv con un problema concreto. Tu tarea es escribir una traducción corregida de cada una.

## Qué hacer

1. Lee `datos/arxiv/correcciones/lote.jsonl`. Cada línea trae:
   - `fuente`: el original en inglés;
   - `traduccion_actual`: la traducción con el problema;
   - `problema`: qué está mal.
2. Para cada línea, escribe una traducción nueva y completa del campo `fuente` que resuelva el problema. Conserva lo que estaba bien de la traducción actual.
3. Escribe `datos/arxiv/correcciones/salida.jsonl`: una línea por trozo, en el mismo orden, con `{"id": ..., "traduccion": ...}`.
4. Comprueba:

   ```bash
   python3 scripts/comprobar_arxiv.py --correcciones
   ```

5. Si algún trozo falla, corrige solo ese y vuelve a comprobar. Muestra el resultado final.

Si crees que un problema marcado no es un error real, deja la traducción actual tal cual y explícalo en tu resumen final.

## Lo que no puedes hacer

- **Traduce tú.** No uses programas, librerías, APIs ni webs de traducción.
- Puedes usar Python **solo para escribir el fichero** con `json.dumps(..., ensure_ascii=False)`.
- No cambies ningún otro fichero del proyecto.

## Reglas de traducción

Las mismas de `instrucciones/arxiv.md`: léelas antes de empezar.
