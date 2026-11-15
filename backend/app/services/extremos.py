"""O último ponto de uma série é o maior ou o menor de um trecho dela?

Decisão em docs/DECISOES.md, 2026-11-15.

A mesma regra de `frontend/lib/descobertas.ts` (`extremoDaSerie`); os casos de teste são os
mesmos nos dois lados. Só diz o fato ("o maior desde 2017"), nunca se é bom ou ruim.

- Série com menos de 4 pontos: nada.
- Último ponto acima de todos os anteriores: "o maior da série, que começa em <primeiro ano>".
- Senão, o ponto anterior mais recente que é maior ou igual a ele; se há pelo menos 3 pontos entre
  os dois (todos abaixo do último), "o maior desde <ano desse ponto>".
- O mesmo para o menor. Empate não é recorde.
"""

from collections.abc import Sequence

MINIMO_PONTOS = 4
MINIMO_ENTRE = 3


def extremo(pontos: Sequence[tuple[int, float]]) -> str | None:
    """`pontos` são (ano, valor) em qualquer ordem; valores nulos devem vir de fora."""
    serie = sorted(pontos)
    if len(serie) < MINIMO_PONTOS:
        return None
    ultimo = serie[-1][1]
    anteriores = serie[:-1]
    if ultimo > max(v for _, v in anteriores):
        return f"o maior da série, que começa em {serie[0][0]}"
    if ultimo < min(v for _, v in anteriores):
        return f"o menor da série, que começa em {serie[0][0]}"
    for tipo, alcanca in (("maior", lambda v: v >= ultimo), ("menor", lambda v: v <= ultimo)):
        # O ponto anterior mais recente que alcança o último; os do meio ficam todos do outro lado.
        for i in range(len(anteriores) - 1, -1, -1):
            if alcanca(anteriores[i][1]):
                if len(anteriores) - 1 - i >= MINIMO_ENTRE:
                    return f"o {tipo} desde {anteriores[i][0]}"
                break
    return None
