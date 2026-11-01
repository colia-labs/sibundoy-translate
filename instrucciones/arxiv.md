# Instrucciones: traducir títulos y resúmenes de arXiv

Vas a traducir del inglés al español títulos y resúmenes de artículos científicos de arXiv, repartidos en lotes de 30 artículos: del `lote_01` al `lote_22` y del `lote_43` al `lote_62` (los números 23 a 42 no existen aquí). Tus traducciones serán los datos con los que se entrena un modelo traductor, así que la calidad importa más que la velocidad.

## Qué hacer

Traduce solo los lotes que aún no tienen salida en `datos/arxiv/salida/`. **Salta los que ya la tienen y no los toques.** Si una sesión se corta, la siguiente sigue donde quedó.

Para cada lote sin salida, de `lote_01` a `lote_22` y de `lote_43` a `lote_62`:

1. Lee `datos/arxiv/lotes/lote_NN.jsonl`. Cada línea es `{"id": ..., "tipo": "titulo" o "resumen", "fuente": ...}`.
2. Traduce el campo `fuente` de cada línea, siguiendo las reglas de abajo.
3. Escribe `datos/arxiv/salida/lote_NN.jsonl`: una línea por trozo, en el mismo orden, con `{"id": ..., "traduccion": ...}`.
4. Comprueba el lote:

   ```bash
   python3 scripts/comprobar_arxiv.py lote_NN
   ```

5. Si algún trozo falla, corrige solo ese y vuelve a comprobar. Como mucho dos correcciones por trozo; si sigue fallando, déjalo y pasa al siguiente lote.

Al terminar, corre `python3 scripts/comprobar_arxiv.py` y muestra el resultado.

## Lo que no puedes hacer

- **Traduce tú.** No uses programas, librerías, APIs ni webs de traducción.
- Puedes usar Python **solo para escribir el fichero** con `json.dumps(..., ensure_ascii=False)`, con tus traducciones escritas por ti dentro del script. Así el JSON queda bien escapado.
- No cambies ningún otro fichero del proyecto.

## Reglas de traducción

### Idioma y estilo

- Español neutro, que se entienda en toda Latinoamérica. Evita las formas propias de España: «vosotros», «ordenador», «móvil».
- Natural y fiel: que suene escrito en español, sin añadir ni quitar ideas.
- Registro académico, como un resumen publicado en una revista en español.

### Términos técnicos

- Si un término tiene un equivalente en español de uso común, tradúcelo («aprendizaje por refuerzo», «conjunto de datos», «red neuronal»).
- Si en español se usa en inglés («prompt», «benchmark», «token», «transformer»), déjalo en inglés, sin comillas ni cursivas.
- **Usa siempre el mismo término para el mismo concepto** en todo el texto.
- **No mezcles idiomas dentro de un término compuesto.** Escribe «codificador-decodificador» o «encoder-decoder», nunca «codificador-decoder».
- Siglas: si la sigla es internacional (LLM, GPU, RNN), déjala igual. Puedes explicarla la primera vez si el original la explica.
- No traduzcas palabra por palabra si el resultado es difícil de entender. Reformula para que se entienda a la primera.

### Fórmulas, nombres y cifras

- Copia **exactamente igual** todo lo que vaya entre `$…$` o sea LaTeX (`\alpha`, `\mathcal{O}(n)`).
- Nombres de modelos, métodos, conjuntos de datos, programas y personas se quedan como están (FlexPart, ImageNet, PyTorch).
- Cifras, unidades y URLs se quedan como están, con el mismo separador decimal que el original: en Latinoamérica unos países usan punto y otros coma.

### Títulos

- Mayúscula solo en la primera palabra, en los nombres propios y en las siglas: «Un marco unificado para la generación de partes 3D», no «Un Marco Unificado Para…».
- Si el título empieza por el nombre del método seguido de dos puntos («FlexPart: A Unified…»), deja el nombre y traduce el resto.

### Forma de la respuesta

- Solo la traducción: sin notas, explicaciones, comillas que la envuelvan ni Markdown.
- Un trozo de entrada es un trozo de salida. No juntes ni partas trozos.
