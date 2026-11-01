"""Alinea los párrafos de un artículo de Global Voices con su original en inglés.

Los traductores a veces quitan, juntan o añaden párrafos, así que no basta el
orden. Cada par se puntúa con anclas que no cambian al traducir: las URL de
los enlaces, las cifras y las palabras con mayúscula. Después se busca el
alineado que respeta el orden y suma más puntos (programación dinámica).
"""
import html
import re

MIN_CHARS = 40


def paragraphs(rendered):
    out = []
    for p in re.findall(r'<p\b[^>]*>(.*?)</p>', rendered, re.S):
        p = p.strip()
        if len(visible(p)) >= MIN_CHARS:
            out.append(p)
    return out


def visible(p):
    return html.unescape(re.sub(r'<[^>]+>', '', p)).strip()


def anchors(p):
    text = visible(p)
    hrefs = set(re.findall(r'href=["\']([^"\']+)', p))
    numbers = set(re.findall(r'\d+', text))
    names = set(re.findall(r'\b[A-ZÁÉÍÓÚÑ][\wáéíóúñ-]{3,}', text))
    return hrefs, numbers, names


def score(es, en):
    (h1, n1, c1), (h2, n2, c2) = anchors(es), anchors(en)
    if h1 != h2:
        return -1.0
    ratio = len(visible(es)) / max(1, len(visible(en)))
    if not 0.8 < ratio < 1.7:
        return -1.0
    s = 3.0 * len(h1) + len(n1 & n2) + 0.5 * len(c1 & c2) - len(n1 ^ n2)
    return s if s >= 1.0 else -1.0


def align(es_paras, en_paras):
    """Pares (es, en) en orden, con puntuación positiva."""
    n, m = len(es_paras), len(en_paras)
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    move = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            options = [(best[i - 1][j], 'es'), (best[i][j - 1], 'en')]
            s = score(es_paras[i - 1], en_paras[j - 1])
            if s > 0:
                options.append((best[i - 1][j - 1] + s, 'par'))
            best[i][j], move[i][j] = max(options)
    pairs, i, j = [], n, m
    while i > 0 and j > 0:
        step = move[i][j]
        if step == 'par':
            pairs.append((es_paras[i - 1], en_paras[j - 1]))
            i, j = i - 1, j - 1
        elif step == 'es':
            i -= 1
        else:
            j -= 1
    return pairs[::-1]
