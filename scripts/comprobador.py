"""Comprueba que una traducción no esté vacía, sin traducir, en inglés o con un largo extraño.

Es la comprobación del lector RSS para el que se hizo el modelo, pasada a
Python con las mismas reglas y los mismos mensajes. Solo cubre texto sin etiquetas: los scripts que la usan
cambian antes cada «<» y «>» por palabras (ver `mask` y `plain`).
"""
import re

# La propiedad White_Space de Unicode, que es lo que quita `trim` en Rust.
WHITESPACE = ('\t\n\v\f\r \x85\xa0        '
              '        　')
# Palabras inglesas muy comunes: si pasan del 12 %, el texto sigue en inglés.
ENGLISH = {'the', 'and', 'of', 'to', 'is', 'that', 'with', 'for', 'this', 'are', 'was', 'have', 'it',
           'which', 'from'}
ENTITY = re.compile(r'&[A-Za-z0-9#]{1,10};')
WORD = re.compile(r'[A-Za-z]+')


def trim(text):
    return text.strip(WHITESPACE)


def clean_output(raw):
    """Quita lo que el modelo añade alrededor: espacios y vallas de código."""
    t = trim(raw)
    if t.startswith('```'):
        body = t[3:].split('\n', 1)[1] if '\n' in t[3:] else ''
        body = body.rstrip(WHITESPACE)
        if body.endswith('```'):
            body = body[:-3]
        return trim(body)
    return t


def visible_text(text):
    # Las entidades (&amp;, &#39;) cuentan como un espacio.
    return ENTITY.sub(' ', text)


def words(text):
    return [w.lower() for w in WORD.findall(text)]


def english_share(text):
    # Con menos de 8 palabras no se juzga: un nombre propio basta para dar un falso aviso.
    w = words(text)
    if len(w) < 8:
        return 0.0
    return sum(x in ENGLISH for x in w) / len(w)


def check(source, translation):
    """Devuelve None si la traducción pasa, o el motivo por el que falla."""
    if '<' in source or '<' in translation:
        raise ValueError('el comprobador solo acepta texto sin etiquetas')
    candidate = clean_output(translation)
    if '*' not in source:
        candidate = candidate.replace('*', '')
    if not trim(candidate):
        return 'vacío'
    text_o, text_t = visible_text(source), visible_text(candidate)
    if english_share(text_t) > 0.12:
        return 'sigue en inglés'
    if len(words(text_o)) >= 4 and trim(text_o) == trim(text_t):
        return 'sin traducir'
    len_o, len_t = len(trim(text_o)), len(trim(text_t))
    if len_o >= 40 and (len_t * 2 < len_o or len_t * 2 > len_o * 5):
        return 'largo extraño: %d → %d caracteres' % (len_o, len_t)
    return None
