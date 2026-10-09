"""Ligação de registros de fontes diferentes à mesma pessoa pública.

Regras (docs/DECISOES.md, "acervo local"), da mais forte para a mais fraca:
- forte, liga sozinha: CPF igual, título de eleitor igual, ligação já feita pela carga do
  TSE (por CPF ou título), CPF mascarado + nome igual, nome + data de nascimento iguais;
- média, só publicada depois de revisão: nome + casa/cargo (`casar_nome`);
- fraca: nome parecido; nunca liga, no máximo sugere.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from ingestion import comum

TITULOS = {"DR", "DRA", "PROF", "PROFA", "PROFESSOR", "PROFESSORA"}


def _palavras(nome: str | None) -> list[str]:
    """Palavras do nome sem partículas ("de", "do") e sem títulos ("Dr.", "Profª")."""
    return [
        p
        for p in comum.chave_nome(nome).split()
        if p.lower() not in comum.PARTICULAS and p not in TITULOS and len(p) > 1
    ]


def casar_nome(nomes: list[str | None], eleitos: list[tuple[int, str]]) -> int | None:
    """Liga o parlamentar ao eleito do TSE pelo nome, em três níveis, e só quando a
    correspondência é única em cada nível:
    1. nome idêntico ("Catarina Guerra");
    2. o mesmo sem partículas e títulos ("Alex Madureira" e "Alex de Madureira");
    3. todas as palavras de um (ao menos duas) contidas no outro ("Valdomiro Lopes" e
       "Dr Valdomiro Lopes"). Nunca por sobrenome solto ("Camilo Santana" não é "Alex
       Santana")."""
    regras = [
        lambda a, b: comum.chave_nome(a) == comum.chave_nome(b),
        lambda a, b: _palavras(a) == _palavras(b) and len(_palavras(a)) >= 2,
        lambda a, b: (
            min(len(_palavras(a)), len(_palavras(b))) >= 2
            and (set(_palavras(a)) <= set(_palavras(b)) or set(_palavras(b)) <= set(_palavras(a)))
        ),
    ]
    for regra in regras:
        for nome in nomes:
            if not nome:
                continue
            ids = {id_ for id_, eleito in eleitos if eleito and regra(nome, eleito)}
            if len(ids) == 1:
                return next(iter(ids))
    return None


Chave = tuple[str, str]  # (fonte, id_externo)


@dataclass
class Aresta:
    a: Chave
    b: Chave
    regra: str


class Grupos:
    """Agrupa registros pelas arestas (union-find). Recusa juntar dois grupos que já têm
    CPFs diferentes: um título ou nome repetido não pode fundir duas pessoas que o CPF
    diz serem distintas."""

    def __init__(self, cpfs: dict[Chave, set[str]]) -> None:
        self.pai: dict[Chave, Chave] = {c: c for c in cpfs}
        self.cpfs: dict[Chave, set[str]] = {c: set(v) for c, v in cpfs.items()}
        self.regra: dict[Chave, str] = {}  # por que cada registro entrou no grupo
        self.recusadas: list[Aresta] = []

    def raiz(self, c: Chave) -> Chave:
        while self.pai[c] != c:
            self.pai[c] = self.pai[self.pai[c]]
            c = self.pai[c]
        return c

    def juntar(self, aresta: Aresta) -> None:
        if aresta.a not in self.pai or aresta.b not in self.pai:
            return
        ra, rb = self.raiz(aresta.a), self.raiz(aresta.b)
        if ra == rb:
            return
        if self.cpfs[ra] and self.cpfs[rb] and self.cpfs[ra] != self.cpfs[rb]:
            self.recusadas.append(aresta)
            return
        self.pai[rb] = ra
        self.cpfs[ra] |= self.cpfs.pop(rb)
        # O grupo de b entrou no de a por esta aresta (cada raiz só é anexada uma vez).
        self.regra[rb] = aresta.regra

    def grupos(self) -> list[list[tuple[Chave, str]]]:
        """Cada grupo é uma pessoa: [(chave, regra)]. A raiz tem regra "origem"; os outros,
        a regra da aresta pela qual o seu grupo entrou."""
        por_raiz: dict[Chave, list[Chave]] = {}
        for c in self.pai:
            por_raiz.setdefault(self.raiz(c), []).append(c)
        return [
            [(c, "origem" if c == raiz else self.regra[c]) for c in membros]
            for raiz, membros in por_raiz.items()
        ]


FORTES = {"cpf", "titulo", "tse", "cpf_parcial_nome", "nome_nascimento"}


def agrupar(
    cpfs: dict[Chave, str | None], arestas: Iterable[Aresta]
) -> tuple[list[list[tuple[Chave, str]]], list[Aresta]]:
    """Agrupa em duas fases e devolve (pessoas, arestas recusadas por conflito de CPF).

    1. Só arestas fortes: formam blocos em que cada registro tem a regra forte pela qual
       entrou ("origem" na raiz).
    2. Arestas médias (nome) ligam blocos inteiros. O maior bloco de cada pessoa fica com
       as regras fortes; todos os registros dos outros blocos recebem a regra média,
       porque a ligação deles à pessoa depende dela."""
    arestas = list(arestas)
    fortes = Grupos({c: {cpf} if cpf else set() for c, cpf in cpfs.items()})
    for aresta in arestas:
        if aresta.regra in FORTES:
            fortes.juntar(aresta)
    blocos = fortes.grupos()
    bloco_de = {c: i for i, bloco in enumerate(blocos) for c, _ in bloco}

    def chave_bloco(i: int) -> Chave:
        return ("bloco", str(i))

    medios = Grupos(
        {chave_bloco(i): {cpf for c, _ in b if (cpf := cpfs.get(c))} for i, b in enumerate(blocos)}
    )
    for aresta in arestas:
        if aresta.regra not in FORTES and aresta.a in bloco_de and aresta.b in bloco_de:
            medios.juntar(
                Aresta(
                    chave_bloco(bloco_de[aresta.a]), chave_bloco(bloco_de[aresta.b]), aresta.regra
                )
            )
    pessoas = []
    for meta in medios.grupos():
        indices = [int(c[1]) for c, _ in meta]
        principal = max(indices, key=lambda i: (len(blocos[i]), -i))
        regra_meta = {int(c[1]): regra for c, regra in meta}
        # Bloco secundário que por acaso é a raiz da 2ª fase: a ligação dele ao principal
        # é a aresta média pela qual o principal entrou.
        media = {i: r if r != "origem" else regra_meta[principal] for i, r in regra_meta.items()}
        pessoa = []
        for i in indices:
            for chave, regra in blocos[i]:
                pessoa.append((chave, regra if i == principal else media[i]))
        pessoas.append(pessoa)
    return pessoas, fortes.recusadas + medios.recusadas
