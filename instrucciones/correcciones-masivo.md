# Instrucciones: corregir traducciones marcadas

Otro modelo tradujo del inglés al español noticias de Wikinews y resúmenes científicos de arXiv y PLOS. Un comprobador automático marcó algunos trozos con un problema concreto. Tu tarea es escribir una traducción corregida de cada uno. Tus correcciones serán datos de entrenamiento de un modelo traductor, así que la calidad importa más que la velocidad.

## Qué hacer

Corrige los lotes **en orden**, empezando por el primero de `datos/masivo/correcciones/lotes/` que aún no tenga salida en `datos/masivo/correcciones/salida/`. Salta los que ya la tienen. Sigue hasta donde puedas.

Para cada lote:

1. Lee `datos/masivo/correcciones/lotes/lote_NNN.jsonl`. Cada línea trae:
   - `fuente`: el original en inglés;
   - `traduccion_actual`: la traducción con el problema (puede estar vacía);
   - `problema`: qué marcó el comprobador;
   - `origen`, `tipo` y `formato`: como en `instrucciones/cola.md`.
2. Para cada línea, escribe una traducción nueva y completa del campo `fuente` que resuelva el problema. Conserva lo que estaba bien de la traducción actual.
3. Escribe `datos/masivo/correcciones/salida/lote_NNN.jsonl`: una línea por trozo, en el mismo orden, con `{"id": ..., "traduccion": ...}`.
4. Comprueba el lote:

   ```bash
   python3 scripts/comprobar_cola.py ../masivo/correcciones lote_NNN
   ```

5. Si algún trozo falla, corrige solo ese y vuelve a comprobar. Como mucho dos correcciones por trozo; si sigue fallando, déjalo y pasa al siguiente.

Algunos problemas son falsas alarmas: por ejemplo, un título lleno de nombres propios marcado por «Mayúscula En Cada Palabra». En ese caso deja la traducción tal cual (si es correcta) y sigue.

Cada 10 lotes, y al terminar, di cuántos lotes llevas.

## Lo que no puedes hacer

- **Traduce tú.** No uses programas, librerías, APIs ni webs de traducción.
- Puedes usar Python **solo para escribir el fichero** con `json.dumps(..., ensure_ascii=False)`.
- No cambies ningún otro fichero del proyecto.

## Reglas de traducción

Las de `instrucciones/cola.md` (reglas generales, de cada origen y de formato): léelas antes de empezar.
