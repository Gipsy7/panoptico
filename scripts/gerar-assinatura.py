"""Gera o sol do Panóptico animado para a assinatura de e-mail (GIF e PNG estático).

Uso: python scripts/gerar-assinatura.py marca/assinatura

O primeiro quadro é a marca completa e parada: o Outlook do Windows mostra só ele.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(sys.argv[1])
LADO = 192  # exibido a 96 px: nítido em tela de alta densidade
SS = 4  # superamostragem para bordas suaves
FUNDO = (28, 26, 23)  # #1c1a17
BRONZE = (201, 149, 74)  # #c9954a
BRILHO = (255, 236, 200)
RAIO_CANTO = 36


def mistura(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))


def quadro(intensidades, anel=0.0):
    n = LADO * SS
    img = Image.new("RGB", (n, n), (255, 255, 255))
    mascara = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, n - 1, n - 1], RAIO_CANTO * SS, fill=255)
    img.paste(FUNDO, mask=mascara)
    d = ImageDraw.Draw(img)
    esc = n / 64 * 0.78
    centro = n / 2
    larg = round(3.2 * esc)
    for i in range(12):
        ang = math.radians(-90 + i * 30)
        p1 = (centro + math.cos(ang) * 15 * esc, centro + math.sin(ang) * 15 * esc)
        p2 = (centro + math.cos(ang) * 28 * esc, centro + math.sin(ang) * 28 * esc)
        cor = mistura(BRONZE, BRILHO, intensidades[i])
        d.line([p1, p2], fill=cor, width=larg)
        for p in (p1, p2):  # pontas arredondadas
            meio = larg / 2
            d.ellipse([p[0] - meio, p[1] - meio, p[0] + meio, p[1] + meio], fill=cor)
    r = 7.5 * esc
    anel_cor = mistura(BRONZE, BRILHO, anel)
    caixa = [centro - r, centro - r, centro + r, centro + r]
    d.ellipse(caixa, outline=anel_cor, width=round(2.56 * esc))
    final = img.resize((LADO, LADO), Image.LANCZOS)
    corte = mascara.resize((LADO, LADO), Image.LANCZOS).point(lambda v: 255 if v >= 128 else 0)
    return final, corte


quadros, duracoes = [quadro([0.0] * 12)], [2200]
passos = 24
for k in range(passos):
    pos = k / passos * 12
    ints = []
    for i in range(12):
        dist = min(abs(i - pos), 12 - abs(i - pos))
        ints.append(max(0.0, 1 - dist / 2.6) ** 1.2)
    quadros.append(quadro(ints, anel=0.35 * math.sin(math.pi * k / passos)))
    duracoes.append(55)

DESTINO.mkdir(parents=True, exist_ok=True)
CHAVE = (255, 0, 255)


def com_chave(par):
    img, corte = par
    fundo = Image.new("RGB", img.size, CHAVE)
    fundo.paste(img, mask=corte)
    return fundo


# Uma paleta só para todos os quadros, para o índice transparente ser o mesmo em todos.
chaveados = [com_chave(q) for q in quadros]
mosaico = Image.new("RGB", (LADO * len(chaveados), LADO))
for i, q in enumerate(chaveados):
    mosaico.paste(q, (i * LADO, 0))
base = mosaico.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
cores = base.getpalette()
indice = min(
    range(96),
    key=lambda i: sum((a - b) ** 2 for a, b in zip(cores[3 * i : 3 * i + 3], CHAVE, strict=True)),
)
paleta = [q.quantize(palette=base, dither=Image.Dither.NONE) for q in chaveados]
for p in paleta:
    p.info["transparency"] = indice
paleta[0].save(
    DESTINO / "panoptico-assinatura.gif",
    save_all=True,
    append_images=paleta[1:],
    duration=duracoes,
    loop=0,
    optimize=True,
    disposal=2,
    transparency=paleta[0].info["transparency"],
)
estatico, corte = quadros[0]
estatico = estatico.convert("RGBA")
estatico.putalpha(corte)
estatico.save(DESTINO / "panoptico-assinatura.png", optimize=True)
for nome in ("panoptico-assinatura.gif", "panoptico-assinatura.png"):
    print(nome, (DESTINO / nome).stat().st_size, "bytes")
