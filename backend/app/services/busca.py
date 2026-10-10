"""Busca por nome em todos os níveis: parlamentares federais, eleitos do TSE (presidente,
governadores, prefeitos, deputados estaduais, vereadores), quem está no cargo hoje nas
câmaras e assembleias com SAPL, partidos e pessoas de eleições passadas.

Cada pessoa aparece uma vez: um eleito que a própria casa já lista como no cargo aparece
pelo dado da casa, que é o atual.

Eficiência (o banco de produção é pago por uso): todo filtro de nome é `busca_norm(coluna)
LIKE '%PALAVRA%'`, a mesma expressão dos índices GIN de trigramas da migração 0033_busca, e
toda consulta tem LIMIT. Mudar a expressão aqui sem mudar o índice faz a busca varrer a tabela."""

from typing import Any
from urllib.parse import quote

from sqlalchemy import and_, case, exists, func, literal, literal_column, select, tuple_, union_all
from sqlalchemy.orm import Session

from app.models import Candidatura, MandatoLocal, Municipio, Parlamentar, Pessoa, PessoaVinculo
from app.services import tse
from app.services.pessoas import publicavel
from ingestion.comum import chave_nome

LIMITE = 20
LIMITE_PARTIDOS = 5
LIMITE_PESSOAS = 10
# Literal (não parâmetro) para o planejador provar que o índice parcial de eleitos serve.
ELEITO = literal_column("'ELEITO%'")
ORDEM_CARGO = {
    "PRESIDENTE": 0,
    "VICE-PRESIDENTE": 1,
    "GOVERNADOR": 2,
    "VICE-GOVERNADOR": 3,
    "DEPUTADO ESTADUAL": 5,
    "DEPUTADO DISTRITAL": 5,
    "PREFEITO": 6,
    "VICE-PREFEITO": 7,
    "VEREADOR": 8,
}
CARGO_LEGIVEL = {
    "PRESIDENTE": "Presidente",
    "VICE-PRESIDENTE": "Vice-presidente",
    "GOVERNADOR": "Governador",
    "VICE-GOVERNADOR": "Vice-governador",
    "DEPUTADO ESTADUAL": "Deputado estadual",
    "DEPUTADO DISTRITAL": "Deputado distrital",
    "PREFEITO": "Prefeito",
    "VICE-PREFEITO": "Vice-prefeito",
    "VEREADOR": "Vereador",
}
# Siglas das prestações de contas (partido_conta_soma) e o nome por extenso. Não há tabela de
# partidos no banco: a lista é estática e só tem siglas que têm página no site.
PARTIDOS = {
    "AGIR": "Agir",
    "AVANTE": "Avante",
    "CIDADANIA": "Cidadania",
    "DC": "Democracia Cristã",
    "DEM": "Democratas",
    "DEMOCRATA": "Democrata",
    "MDB": "Movimento Democrático Brasileiro",
    "MOBILIZA": "Mobilização Nacional",
    "NOVO": "Partido Novo",
    "PATRIOTA": "Patriota",
    "PC do B": "Partido Comunista do Brasil",
    "PCB": "Partido Comunista Brasileiro",
    "PCO": "Partido da Causa Operária",
    "PDT": "Partido Democrático Trabalhista",
    "PL": "Partido Liberal",
    "PODE": "Podemos",
    "PP": "Progressistas",
    "PRD": "Partido Renovação Democrática",
    "PRTB": "Partido Renovador Trabalhista Brasileiro",
    "PSB": "Partido Socialista Brasileiro",
    "PSC": "Partido Social Cristão",
    "PSD": "Partido Social Democrático",
    "PSDB": "Partido da Social Democracia Brasileira",
    "PSL": "Partido Social Liberal",
    "PSOL": "Partido Socialismo e Liberdade",
    "PSTU": "Partido Socialista dos Trabalhadores Unificado",
    "PT": "Partido dos Trabalhadores",
    "PTB": "Partido Trabalhista Brasileiro",
    "PV": "Partido Verde",
    "REDE": "Rede Sustentabilidade",
    "REPUBLICANOS": "Republicanos",
    "SDD": "Solidariedade",
    "UNIÃO": "União Brasil",
    "UP": "Unidade Popular",
}  # fmt: skip
FONTES_COM_PERFIL = ("candidatura", "parlamentar", "mandato_local")


def _casa(coluna: Any, palavras: list[str]) -> Any:
    """Todas as palavras aparecem no nome, sem diferença de acento ou maiúscula."""
    normal = func.busca_norm(coluna)
    return and_(*(normal.like(f"%{p}%") for p in palavras))


def _partidos(palavras: list[str]) -> list[dict]:
    """Partidos pela sigla (inteira, mesmo com 2 letras: 'pt') ou por parte do nome."""
    termo = " ".join(palavras)
    longo = sum(len(p) for p in palavras) >= 3
    achados = []
    for sigla, nome in PARTIDOS.items():
        chave_sigla = chave_nome(sigla)
        if termo == chave_sigla:
            ordem = 0
        elif longo and all(p in f"{chave_sigla} {chave_nome(nome)}" for p in palavras):
            ordem = 1 if chave_sigla.startswith(palavras[0]) else 2
        else:
            continue
        achados.append((ordem, sigla, nome))
    achados.sort()
    return [
        {"sigla": sigla, "nome": nome, "caminho": f"/partidos/{quote(sigla)}"}
        for _, sigla, nome in achados[:LIMITE_PARTIDOS]
    ]


def _perfis_das_pessoas(session: Session, vinculos: list[PessoaVinculo]) -> dict[int, list]:
    """Para cada pessoa, os perfis do site a que os vínculos levam: (prioridade, item)."""
    chaves = [
        (int(ano), sq)
        for v in vinculos
        if v.fonte == "candidatura"
        for ano, sq in [v.id_externo.split(":", 1)]
    ]
    candidaturas = {}
    if chaves:
        candidaturas = {
            (c.ano_eleicao, c.sq_candidato): c
            for c in session.scalars(
                select(Candidatura).where(
                    tuple_(Candidatura.ano_eleicao, Candidatura.sq_candidato).in_(chaves),
                    Candidatura.cargo.in_(tse.CARGOS_COM_PERFIL),
                )
            )
        }
    ids_parl = [v.id_externo.split(":", 1)[1] for v in vinculos if v.fonte == "parlamentar"]
    parlamentares = {}
    if ids_parl:
        parlamentares = {
            f"{p.casa}:{p.id_externo}": p
            for p in session.scalars(
                select(Parlamentar).where(Parlamentar.id_externo.in_(ids_parl))
            )
        }
    ids_locais = [v.id_externo.rsplit(":", 1)[1] for v in vinculos if v.fonte == "mandato_local"]
    locais = {}
    if ids_locais:
        locais = {
            f"{m.casa}:{m.uf}:{m.municipio_ibge or ''}:{m.id_externo}": m
            for m in session.scalars(
                select(MandatoLocal).where(MandatoLocal.id_externo.in_(ids_locais))
            )
        }
    perfis: dict[int, list] = {}
    for v in vinculos:
        item = None
        if v.fonte == "parlamentar" and v.id_externo in parlamentares:
            p = parlamentares[v.id_externo]
            cargo = "Deputado federal" if p.casa == "camara" else "Senador"
            item = (0, cargo, p.uf, p.partido, f"/parlamentar/{p.id}")
        elif v.fonte == "mandato_local" and v.id_externo in locais:
            m = locais[v.id_externo]
            camara = m.casa == "camara"
            cargo = "Vereador" if camara else "Deputado estadual"
            rota = "vereador" if camara else "deputado-estadual"
            item = (1, cargo, m.uf, m.partido, f"/{rota}/{m.id}")
        elif v.fonte == "candidatura":
            ano, sq = v.id_externo.split(":", 1)
            c = candidaturas.get((int(ano), sq))
            if c:
                municipal = c.cargo in ("PREFEITO", "VICE-PREFEITO", "VEREADOR")
                lugar = f"{c.unidade}/{c.uf}" if municipal else c.uf
                eleito = (c.situacao_turno or "").startswith("ELEITO")
                cargo = CARGO_LEGIVEL.get(c.cargo, c.cargo.capitalize())
                cargo += f", {'eleição' if eleito else 'candidatura'} de {c.ano_eleicao}"
                item = (2 + 3000 - c.ano_eleicao, cargo, lugar, c.partido, f"/eleito/{c.id}")
        if item:
            perfis.setdefault(v.pessoa_id, []).append(item)
    return perfis


def _pessoas(session: Session, palavras: list[str], ja_listados: set[str]) -> list[dict]:
    """Pessoas com vínculo publicável a um perfil do site que os grupos de cima não mostram
    (eleições passadas, suplentes). Sem perfil no site não há para onde levar: ficam de fora."""
    pessoas = session.scalars(
        select(Pessoa)
        .where(
            and_(*(Pessoa.chave_nome.like(f"%{p}%") for p in palavras)),
            exists().where(
                PessoaVinculo.pessoa_id == Pessoa.id,
                PessoaVinculo.fonte.in_(FONTES_COM_PERFIL),
                publicavel(),
            ),
        )
        .order_by(Pessoa.nome)
        .limit(LIMITE_PESSOAS * 4)
    ).all()
    if not pessoas:
        return []
    vinculos = session.scalars(
        select(PessoaVinculo).where(
            PessoaVinculo.pessoa_id.in_([p.id for p in pessoas]),
            PessoaVinculo.fonte.in_(FONTES_COM_PERFIL),
            publicavel(),
        )
    ).all()
    perfis = _perfis_das_pessoas(session, list(vinculos))
    resultado = []
    for pessoa in pessoas:
        lista = sorted(perfis.get(pessoa.id, []))
        if not lista or any(i[4] in ja_listados for i in lista):
            continue
        _, cargo, lugar, partido, caminho = lista[0]
        resultado.append(
            {
                "nome": pessoa.nome,
                "nome_completo": None,
                "cargo": cargo,
                "partido": partido,
                "lugar": lugar,
                "caminho": caminho,
            }
        )
        if len(resultado) == LIMITE_PESSOAS:
            break
    return resultado


def buscar(session: Session, nome: str) -> dict:
    palavras = chave_nome(nome).split()
    if not palavras:
        return {"itens": [], "partidos": [], "pessoas": []}
    partidos = _partidos(palavras)
    # Trigrama precisa de 3 letras: sem nenhuma palavra assim ('pt', 'da') só a sigla de partido
    # faz sentido. Palavras curtas ('da', 'de') junto de outras maiores não entram no filtro
    # SQL (casariam com quase todo mundo e não usam o índice).
    if all(len(p) < 3 for p in palavras):
        return {"itens": [], "partidos": partidos, "pessoas": []}
    palavras = [p for p in palavras if len(p) >= 3]
    resultado: list[dict] = []

    federais = session.scalars(
        select(Parlamentar)
        .where(Parlamentar.em_exercicio, _casa(Parlamentar.nome_parlamentar, palavras))
        .order_by(Parlamentar.nome_parlamentar)
        .limit(LIMITE)
    ).all()
    for p in federais:
        resultado.append(
            {
                "nome": p.nome_parlamentar,
                "nome_completo": p.nome_civil,
                "cargo": "Deputado federal" if p.casa == "camara" else "Senador",
                "partido": p.partido,
                "lugar": p.uf,
                "caminho": f"/parlamentar/{p.id}",
            }
        )

    mandatos = session.execute(
        select(MandatoLocal, Municipio.nome)
        .outerjoin(Municipio, Municipio.ibge == MandatoLocal.municipio_ibge)
        .where(
            MandatoLocal.em_exercicio,
            _casa(MandatoLocal.nome, palavras) | _casa(MandatoLocal.nome_completo, palavras),
        )
        .order_by(MandatoLocal.nome)
        .limit(LIMITE)
    ).all()
    ja_listados: set[int] = set()
    locais = []
    for m, cidade in mandatos:
        camara = m.casa == "camara"
        if m.candidatura_id:
            ja_listados.add(m.candidatura_id)
        locais.append(
            {
                "nome": m.nome,
                "nome_completo": m.nome_completo,
                "cargo": "Vereador"
                if camara
                else ("Deputado distrital" if m.uf == "DF" else "Deputado estadual"),
                "partido": m.partido,
                "lugar": f"{cidade}/{m.uf}" if cidade else m.uf,
                "caminho": f"/{'vereador' if camara else 'deputado-estadual'}/{m.id}",
                "_ordem": ORDEM_CARGO["VEREADOR" if camara else "DEPUTADO ESTADUAL"],
            }
        )

    eleito = Candidatura.situacao_turno.like(ELEITO)
    # Eleição mais recente com posse, por cargo: uma sondagem no índice por cargo, em vez de
    # varrer a tabela inteira a cada busca.
    ultima = union_all(
        *(
            select(
                literal(cargo).label("cargo"),
                select(func.max(Candidatura.ano_eleicao))
                .where(Candidatura.cargo == cargo, eleito, tse.mandato_em_curso())
                .scalar_subquery()
                .label("ano"),
            )
            for cargo in tse.CARGOS_COM_PERFIL
        )
    ).subquery()
    candidaturas = session.scalars(
        select(Candidatura)
        .where(
            eleito,
            Candidatura.cargo.in_(tse.CARGOS_COM_PERFIL),
            exists().where(
                ultima.c.cargo == Candidatura.cargo, ultima.c.ano == Candidatura.ano_eleicao
            ),
            _casa(Candidatura.nome_urna, palavras) | _casa(Candidatura.nome, palavras),
        )
        .order_by(case(ORDEM_CARGO, value=Candidatura.cargo, else_=9), Candidatura.nome_urna)
        .limit(LIMITE * 2)
    ).all()
    for c in candidaturas:
        if c.id in ja_listados:
            continue
        municipal = c.cargo in ("PREFEITO", "VICE-PREFEITO", "VEREADOR")
        locais.append(
            {
                "nome": c.nome_urna,
                "nome_completo": c.nome,
                "cargo": CARGO_LEGIVEL.get(c.cargo, c.cargo.capitalize()),
                "partido": c.partido,
                "lugar": f"{c.unidade}/{c.uf}"
                if municipal
                else ("Brasil" if "PRESIDENTE" in c.cargo else c.uf),
                "caminho": f"/eleito/{c.id}",
                "_ordem": ORDEM_CARGO.get(c.cargo, 9),
            }
        )

    locais.sort(key=lambda x: (x["_ordem"], chave_nome(x["nome"])))
    itens = (resultado + locais)[:LIMITE]
    for item in itens:
        item.pop("_ordem", None)
        # O nome completo só ajuda quando é diferente do nome de urna ou parlamentar.
        if chave_nome(item["nome_completo"]) == chave_nome(item["nome"]):
            item["nome_completo"] = None
    listados = {i["caminho"] for i in itens}
    return {"itens": itens, "partidos": partidos, "pessoas": _pessoas(session, palavras, listados)}
