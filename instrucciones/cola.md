# Instrucciones: traducir la cola de lotes

Vas a traducir del inglés al español textos de muchas especialidades: noticias de Wikinews, resúmenes científicos de arXiv (física, matemáticas, informática, economía…) y resúmenes de PLOS (medicina, psicología, educación, derecho, filosofía…). Tus traducciones serán los datos con los que se entrena un modelo traductor, así que la calidad importa más que la velocidad.

Hay tres sesiones traduciendo a la vez, cada una en su carpeta. **El mensaje con el que te abrieron dice tu número de sesión (1, 2 o 3).** Trabaja solo en `datos/cola/N/`, con tu número en lugar de N.

## Qué hacer

1. Al empezar, escribe en `datos/cola/N/PROFESOR.txt` una línea con tu nombre de modelo y la fecha. Si el fichero ya existe, añade la línea al final.
2. Traduce los lotes **en orden**, empezando por el primero de `datos/cola/N/lotes/` que aún no tenga salida en `datos/cola/N/salida/`. **Salta los que ya la tienen y no los toques.** Sigue hasta donde puedas: no hace falta terminar todos.

Para cada lote:

1. Lee `datos/cola/N/lotes/lote_NNNN.jsonl`. Cada línea es `{"id", "origen", "tipo", "formato", "fuente"}`:
   - `origen`: `wikinews`, `arxiv` o `plos`. Dice qué reglas de abajo aplicar.
   - `tipo`: `titulo`, `parrafo` o `resumen`.
   - `formato`: `html`, `markdown` o `texto`.
2. Traduce el campo `fuente` de cada línea, siguiendo las reglas generales y las de su origen.
3. Escribe `datos/cola/N/salida/lote_NNNN.jsonl`: una línea por trozo, en el mismo orden, con `{"id": ..., "traduccion": ...}`.
4. Comprueba el lote:

   ```bash
   python3 scripts/comprobar_cola.py N lote_NNNN
   ```

5. Si algún trozo falla, corrige solo ese y vuelve a comprobar. Como mucho dos correcciones por trozo; si sigue fallando, déjalo y pasa al siguiente lote.

Cada 10 lotes, y al terminar la sesión, di cuántos lotes llevas y el último que hiciste.

## Lo que no puedes hacer

- **Traduce tú.** No uses programas, librerías, APIs ni webs de traducción.
- Puedes usar Python **solo para escribir el fichero** con `json.dumps(..., ensure_ascii=False)`, con tus traducciones escritas por ti dentro del script. Así el JSON queda bien escapado.
- No cambies ningún otro fichero del proyecto, ni las carpetas de las otras sesiones.

## Reglas generales

### Idioma y estilo

- Español neutro, que se entienda en toda Latinoamérica. Evita las formas propias de España: «vosotros», «ordenador», «móvil», «coche».
- Natural y fiel: que suene escrito en español, sin añadir ni quitar ideas.
- No traduzcas palabra por palabra si el resultado es difícil de entender. Reformula para que se entienda a la primera.

### Términos

- Usa el término que emplean en español los profesionales de cada área: médicos, abogados, psicólogos, economistas, físicos.
- **Usa siempre el mismo término para el mismo concepto** en todo el texto.
- **No mezcles idiomas dentro de un término compuesto.** Escribe «codificador-decodificador» o «encoder-decoder», nunca «codificador-decoder».
- Nombres de personas, empresas, programas, métodos, modelos, conjuntos de datos, especies, genes y proteínas se quedan como están.
- Siglas: usa la sigla en español si es la habitual (ONU, OTAN, ADN, VIH, OMS); si no, deja la original (FBI, NASA, LLM, GPU).

### Cifras

- **Los mismos números que el original y con el mismo separador decimal y de miles**: «7,250,000» se queda «7,250,000» y «0.05» se queda «0.05». En Latinoamérica unos países usan punto y otros coma.
- Unidades y horas como en el original («5 mg», «37 °C», «8 a.m.»).

### Títulos

- Mayúscula solo en la primera palabra, en los nombres propios y en las siglas: «Un marco unificado para la generación de partes 3D», no «Un Marco Unificado Para…».

### Forma de la respuesta

- Solo la traducción: sin notas, explicaciones ni comillas que la envuelvan.
- Un trozo de entrada es un trozo de salida. No juntes ni partas trozos.

## Reglas de cada origen

### `wikinews`: noticias

- Registro periodístico, como una agencia de noticias en español.
- Lugares y organismos con nombre habitual en español se traducen: «New York» → «Nueva York», «United Nations» → «Naciones Unidas», «the White House» → «la Casa Blanca».
- Fechas en orden español: «Monday, April 13» → «el lunes 13 de abril»; «February 18, 2008» → «18 de febrero de 2008».
- Las citas entre comillas también se traducen. Usa las mismas comillas en toda la noticia.

### `arxiv`: resúmenes científicos

- Registro académico, como un resumen publicado en una revista en español.
- Si un término técnico tiene un equivalente en español de uso común, tradúcelo («aprendizaje por refuerzo», «conjunto de datos», «red neuronal»). Si en español se usa en inglés («prompt», «benchmark», «token», «transformer»), déjalo en inglés, sin comillas ni cursivas.
- Copia **exactamente igual** todo lo que vaya entre `$…$` o sea LaTeX (`\alpha`, `\mathcal{O}(n)`).
- Si el título empieza por el nombre del método seguido de dos puntos («FlexPart: A Unified…»), deja el nombre y traduce el resto.

### `plos`: resúmenes de biología, medicina y ciencias sociales

- Registro de artículo científico. Si el resumen está escrito para el público general, mantén ese tono claro y sencillo.
- Los nombres científicos de especies van igual, sin cursivas ni otras marcas: Aspergillus nidulans, Plasmodium falciparum.

## Formato

El campo `formato` dice qué marcas lleva el trozo. **La traducción lleva exactamente las mismas marcas, en el mismo orden.**

- **`html`**: copia cada `<a href="...">`, `<em>` y `<strong>` tal cual, con la misma URL, y traduce el texto de dentro. Si el orden de las palabras cambia, mueve la etiqueta con su texto.
  - `<a href="https://en.wikinews.org/wiki/New_York">New York</a>` → `<a href="https://en.wikinews.org/wiki/New_York">Nueva York</a>`
- **`markdown`**: igual con `[texto](url)`, `*cursiva*` y `**negrita**`. La URL no se toca.
- **`texto`**: sin marcas; no añadas ninguna.
