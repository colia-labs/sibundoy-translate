#!/usr/bin/env python3
"""Gráficas de la card de Hugging Face, sin texto en ningún idioma (solo nombres, siglas y cifras).

Uso: python3 graficas_card.py PERDIDA_BASE.json PERDIDA_INSTRUCT.json CARPETA_FUENTES SALIDA/
Cifras: resultados/profesores/TABLA.md y los COMET de los exámenes externos (post del blog, «Qué tan bien traduce»).
"""
import json, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

# Colores y pesos del manual de marca (colia-labs/colia, marca/MARCA.md): Sibundoy en tinta, el resto en gris claro, sobre blanco.
SIB, GRIS = '#121212', '#9A9A9A'
TINTA, SECUNDARIO, LINEA, PAPEL = '#121212', '#666666', '#E0E0E0', '#FFFFFF'
NOMBRE = 'Sibundoy-Translate-1.7B'

COMET_RIVALES = {  # WMT24++, Medline, FLORES+, NTREX, TICO-19
    NOMBRE: [80.4, 86.9, 86.0, 86.1, 88.1],
    'Tower+ 2B': [81.7, 87.2, 86.8, 86.8, 88.9],
    'Gemma 4 E2B': [82.4, 87.2, 86.6, 86.2, 88.4],
    'TranslateGemma 4B': [82.8, 87.5, 87.3, 86.6, 88.2],
    'Gemma 4 E4B': [82.9, 87.4, 87.1, 87.0, 88.7],
}
EXAMENES = ['WMT24++', 'Medline', 'FLORES+', 'NTREX', 'TICO-19']
MEJORA = [  # examen, LFM3-1.7B, Sibundoy, mejora calculada sin redondear (puede diferir 0,1 de la resta)
    ('WMT24++', 74.9, 80.4, 5.5), ('ColIA-213', 84.8, 87.6, 2.8), ('Medline', 81.1, 86.9, 5.8),
    ('NTREX', 81.4, 86.1, 4.6), ('FLORES+', 82.9, 86.0, 3.2), ('TICO-19', 85.2, 88.1, 2.9),
]
FORMATO = [(NOMBRE, 210), ('Gemma 4 E4B', 208), ('LFM3-1.7B', 207), ('Gemma 4 E2B', 195),
           ('TranslateGemma 4B', 191), ('Tower+ 2B', 189)]


def fuentes(carpeta, tmp):
    # matplotlib no lee woff2 ni fuentes variables: se fija cada peso y se pasa a ttf.
    for peso in (400, 600):
        f = instancer.instantiateVariableFont(TTFont(Path(carpeta) / ('AtkinsonHyperlegibleNext-%d-latin.woff2' % peso)), {'wght': peso})
        f.flavor = None
        f['OS/2'].usWeightClass = peso
        destino = Path(tmp) / ('atkinson-%d.ttf' % peso)
        f.save(destino)
        font_manager.fontManager.addfont(str(destino))
    plt.rcParams.update({
        'font.family': 'Atkinson Hyperlegible Next', 'font.size': 11, 'text.color': TINTA,
        'axes.edgecolor': LINEA, 'axes.labelcolor': SECUNDARIO, 'xtick.color': SECUNDARIO, 'ytick.color': TINTA,
        'figure.facecolor': PAPEL, 'axes.facecolor': PAPEL, 'savefig.facecolor': PAPEL,
    })


def limpiar(ax, ejes=('left', 'top', 'right')):
    for lado in ejes:
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0)


def rivales(salida):
    modelos = list(COMET_RIVALES)[::-1]
    fig, axes = plt.subplots(1, 5, figsize=(13, 3.6), sharey=True)
    for j, (ax, examen) in enumerate(zip(axes, EXAMENES)):
        vals = [COMET_RIVALES[m][j] for m in modelos]
        lo, hi = min(vals), max(vals)
        ax.set_xlim(lo - 1.2, hi + 1.2)
        ax.grid(axis='x', color=LINEA, linewidth=0.8)
        ax.set_axisbelow(True)
        for i, (m, v) in enumerate(zip(modelos, vals)):
            propio = m == NOMBRE
            ax.scatter(v, i, s=90 if propio else 55, color=SIB if propio else GRIS, zorder=3,
                       edgecolor=PAPEL, linewidth=2)
            ax.annotate('%.1f' % v, (v, i), xytext=(0, 9), textcoords='offset points', ha='center',
                        fontsize=10, color=TINTA if propio else SECUNDARIO, fontweight=600 if propio else 'normal')
        ax.set_title(examen, fontsize=12, fontweight=600, loc='left')
        ax.set_ylim(-0.6, len(modelos) - 0.4)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        limpiar(ax)
    axes[0].set_yticks(range(len(modelos)), modelos)
    for t in axes[0].get_yticklabels():
        if t.get_text() == NOMBRE:
            t.set_color(SIB); t.set_fontweight(600)
    fig.suptitle('COMET  ·  en-es', x=0.01, ha='left', fontsize=14, fontweight=600)
    fig.tight_layout()
    fig.savefig(salida / 'comet-rivales.png', dpi=200)


def mejora(salida):
    fig, ax = plt.subplots(figsize=(8, 4))
    filas = MEJORA[::-1]
    for i, (examen, antes, ahora, delta) in enumerate(filas):
        ax.plot([antes, ahora], [i, i], color=LINEA, linewidth=3, solid_capstyle='round', zorder=1)
        ax.scatter(antes, i, s=60, color=GRIS, zorder=2, edgecolor=PAPEL, linewidth=2)
        ax.scatter(ahora, i, s=80, color=SIB, zorder=3, edgecolor=PAPEL, linewidth=2)
        ax.annotate('%.1f' % antes, (antes, i), xytext=(-8, 0), textcoords='offset points', ha='right', va='center',
                    fontsize=10, color=SECUNDARIO)
        ax.annotate('%.1f  (+%.1f)' % (ahora, delta), (ahora, i), xytext=(8, 0), textcoords='offset points',
                    va='center', fontsize=10, color=TINTA, fontweight=600)
    ax.set_yticks(range(len(filas)), [f[0] for f in filas])
    ax.set_xlim(72, 92)
    ax.grid(axis='x', color=LINEA, linewidth=0.8)
    ax.set_axisbelow(True)
    limpiar(ax)
    ax.scatter([], [], color=GRIS, s=60, label='LFM3-1.7B')
    ax.scatter([], [], color=SIB, s=80, label=NOMBRE)
    fig.suptitle('COMET  ·  en-es', x=0.01, ha='left', fontsize=14, fontweight=600)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.legend(loc='upper right', ncol=2, frameon=False, fontsize=10)
    fig.savefig(salida / 'comet-lfm3.png', dpi=200)


def formato(salida):
    fig, ax = plt.subplots(figsize=(8, 3.4))
    filas = FORMATO[::-1]
    for i, (m, n) in enumerate(filas):
        propio = m == NOMBRE
        ax.barh(i, n, height=0.6, color=SIB if propio else GRIS, zorder=2)
        ax.annotate('%d / 213' % n, (n, i), xytext=(6, 0), textcoords='offset points', va='center', fontsize=10,
                    color=TINTA if propio else SECUNDARIO, fontweight=600 if propio else 'normal')
    ax.set_yticks(range(len(filas)), [f[0] for f in filas])
    for t in ax.get_yticklabels():
        if t.get_text() == NOMBRE:
            t.set_color(SIB); t.set_fontweight(600)
    ax.set_xlim(0, 240)
    ax.set_xticks([0, 50, 100, 150, 213])
    ax.grid(axis='x', color=LINEA, linewidth=0.8)
    ax.set_axisbelow(True)
    limpiar(ax)
    fig.suptitle('HTML · Markdown', x=0.01, ha='left', fontsize=14, fontweight=600)
    fig.tight_layout()
    fig.savefig(salida / 'formato.png', dpi=200)


def entrenamiento(base, instruct, salida):
    fig, ax = plt.subplots(figsize=(8, 4))
    for nombre, ruta, color, trazo in (('Base', base, SIB, '-'), ('Instruct', instruct, GRIS, '--')):
        filas = json.load(open(ruta))
        tren = [(r['step'], r['loss']) for r in filas if 'loss' in r]
        ev = [(r['step'], r['eval_loss']) for r in filas if 'eval_loss' in r]
        k = 10  # media móvil de 10 registros (100 pasos)
        pasos = [p for p, _ in tren][k - 1:]
        media = [sum(v for _, v in tren[i - k + 1:i + 1]) / k for i in range(k - 1, len(tren))]
        ax.plot(pasos, media, color=color, linestyle=trazo, linewidth=2)
        ax.scatter([p for p, _ in ev], [v for _, v in ev], color=color, s=40, zorder=3, edgecolor=PAPEL, linewidth=1.5)
        ax.annotate('%s  %.3f' % (nombre, ev[-1][1]), ev[-1], xytext=(10, 0), textcoords='offset points', va='center',
                    fontsize=10, color=TINTA, fontweight=600)
    ax.set_xlabel('step')
    ax.set_ylabel('loss')
    ax.set_ylim(0.28, 0.5)
    ax.set_xlim(0, 5200)
    ax.grid(axis='y', color=LINEA, linewidth=0.8)
    ax.set_axisbelow(True)
    limpiar(ax, ('top', 'right'))
    ax.plot([], [], color=SECUNDARIO, linewidth=2, label='train')
    ax.scatter([], [], color=SECUNDARIO, s=40, label='eval')
    ax.legend(loc='upper right', frameon=False, fontsize=10)
    fig.suptitle('Base  vs  Instruct  ·  LoRA r=64', x=0.01, ha='left', fontsize=14, fontweight=600)
    fig.tight_layout()
    fig.savefig(salida / 'entrenamiento.png', dpi=200)


def main():
    base, instruct, carpeta, salida = sys.argv[1:5]
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    fuentes(carpeta, salida)
    rivales(salida); mejora(salida); formato(salida); entrenamiento(base, instruct, salida)
    for f in salida.glob('*.ttf'):
        f.unlink()
    print('LISTO')


if __name__ == '__main__':
    main()
