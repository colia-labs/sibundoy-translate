#!/usr/bin/env python3
"""Mide rasgos regionales del español en textos.

spain_hits cuenta marcas fuertes de España: el vosotros (pronombres y verbos
en -áis/-éis), el pronombre «os» y palabras que en Latinoamérica casi no se
usan. latam_hits cuenta regionalismos de Latinoamérica, por zona: el voseo y
palabras que fuera de su país suenan locales. Las palabras ambiguas no
cuentan (vale, piso, conducir, camión, colectivo, pana, celular, carro, neta,
vaina, recámara): se busca lo que rompe el español neutro, no lo
latinoamericano general.
"""
import re

SPAIN = [
    r'\bvosotr[oa]s\b', r'\bvuestr[oa]s?\b', r'\bos\b',
    r'\b\w+(?:áis|éis)\b',
    r'\bordenador(?:es)?\b', r'\bzumos?\b', r'\bpatatas?\b', r'\bcoches?\b',
    r'\bmóvil(?:es)?\b', r'\bgafas\b', r'\bmola\b', r'\bguay\b', r'\bvale la pena\b(?!)',
]
SPAIN = [re.compile(p, re.I) for p in SPAIN if '(?!)' not in p]
LATAM = {
    'voseo': [r'\b(?:tenés|querés|podés|sabés|hacés|decís|venís|salís|sentís|pensás|creés|mirá|fijate|vení|andá|sos)\b',
              r'(?<![\w-])vos\b(?! (?:sabes|tienes))'],
    'rioplatense': [r'\bche\b', r'\blaburo\b', r'\blabur(?:ar|a|an|ó)\b', r'\bpib[ea]s?\b', r'\bquilombo\b',
                    r'\bboludo\b', r'\bbondi\b', r'\bpileta\b', r'\bfrutillas?\b', r'\bmorfar\b'],
    'mexicano': [r'\bahorita\b', r'\bplatic(?:ar|ó|amos|an|a)\b', r'\bpláticas?\b', r'\bchamba\b', r'\bchid[oa]s?\b',
                 r'\bgüey\b', r'\bpadrísim[oa]\b', r'\bpopotes?\b', r'\bcuates?\b', r'\balbercas?\b',
                 r'\bórale\b', r'\bchamac[oa]s?\b'],
    'caribe': [r'\bguaguas?\b', r'\bzafacón\b', r'\bchévere\b'],
    'colombo_venezolano': [r'\bparcer[oa]s?\b', r'\bparce\b', r'\bbacan[oa]\b', r'\bchimba\b', r'\bcham[oa]s?\b'],
    'chileno': [r'\bcachai\b', r'\bweón\b', r'\bfome\b', r'\bpolol[oa]s?\b', r'\bal tiro\b'],
    'andino_general': [r'\bnomás\b', r'\bno más que\b(?!)'],
}
LATAM = {k: [re.compile(p, re.I) for p in v if '(?!)' not in p] for k, v in LATAM.items()}
LATAM_TLD = ('.mx', '.co', '.ar', '.cl', '.pe', '.ve', '.ec', '.uy', '.py', '.bo', '.gt', '.cr', '.do', '.hn', '.sv', '.ni', '.pa', '.cu', '.pr')


def spain_hits(text):
    return [m.group(0) for p in SPAIN for m in p.finditer(text)]


def latam_hits(text):
    """Lista de (zona, palabra) con los regionalismos latinoamericanos del texto."""
    return [(zone, m.group(0)) for zone, pats in LATAM.items() for p in pats for m in p.finditer(text)]


def country(url):
    host = re.sub(r'^https?://', '', url or '').split('/')[0].split(':')[0].lower()
    if host.endswith('.es') or '/es-es/' in (url or ''):
        return 'España'
    if host.endswith(LATAM_TLD) or any(host.endswith(t + '.') for t in LATAM_TLD):
        return 'Latam'
    return 'genérico'
