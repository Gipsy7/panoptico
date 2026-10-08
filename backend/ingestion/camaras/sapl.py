"""Câmaras municipais que usam o SAPL (Interlegis): vereadores no cargo hoje e projetos.

Um conector para todas: a API do SAPL é a mesma em cada câmara. Os endereços vêm do
catálogo versionado de canais oficiais (tipo "sapl"). Para cada câmara:
1. a legislatura atual e os mandatos dela (titular ou suplente, datas);
2. os dados de cada vereador (nome, foto, contato) e a filiação partidária atual;
3. as votações nominais do ano atual e do anterior, com o voto de cada um, e a presença
   nas sessões plenárias;
4. as autorias de cada vereador: o texto da autoria já diz o tipo e o ano ("Requerimento
   nº 324 de 2026"), então requerimentos, indicações e moções viram só contagem; os
   projetos de lei (e afins) do ano atual e do anterior são guardados com a ementa.

Educação com os servidores municipais: uma requisição por vez em cada câmara, com pausa,
e várias câmaras em paralelo. Roda uma vez por semana.
"""

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from typing import Any

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Candidatura,
    FonteIngestao,
    GastoLocal,
    MandatoLocal,
    Municipio,
    ProjetoLocal,
    VotacaoLocal,
    VotoLocal,
)
from ingestion import comum
from ingestion.canais import catalogo

FONTE = "sapl_camaras"
PAUSA = 0.4
POR_PAGINA = 100
AUTORIA = re.compile(r" - (?P<tipo>.+?) n\S*\s*(?P<numero>\d+)\s+de\s+(?P<ano>\d{4})\s*$", re.I)
# "Ordem: Ordem do Dia/Expediente: 1 - Requerimento nº 62 de 2025 em 33ª Ordinária da 3ª
# Sessão Legislativa da 16ª Legislatura - Votação: Aprovado"
REGISTRO = re.compile(r" - (?P<materia>.+?) em \d+\S* .*?(?: - Votação: (?P<resultado>.+))?$")
TIPOS_PROJETO = re.compile(
    r"projeto de lei|projeto de resolu|projeto de decreto|emenda (à|a) lei org|proposta de emenda",
    re.I,
)


class Sapl:
    def __init__(self, base: str, client: httpx.Client) -> None:
        self.base = base.rstrip("/") + "/api/"
        self.client = client

    def get(self, caminho: str, **params: Any) -> dict:
        time.sleep(PAUSA)
        return comum.get_json(self.client, self.base + caminho, params=params or None)

    def todos(self, caminho: str, **params: Any) -> list[dict]:
        itens, pagina = [], 1
        while True:
            dados = self.get(caminho, page_size=POR_PAGINA, page=pagina, **params)
            itens += dados.get("results", [])
            if not dados.get("pagination", {}).get("next_page"):
                return itens
            pagina += 1


def _https(url: str | None) -> str | None:
    """O SAPL devolve links com http://; o site é https e o navegador bloquearia."""
    if not url:
        return None
    return "https://" + url.removeprefix("http://") if url.startswith("http://") else url


def legislatura_atual(legislaturas: list[dict], hoje: date) -> dict | None:
    vigentes = [
        lg for lg in legislaturas
        if date.fromisoformat(lg["data_inicio"]) <= hoje <= date.fromisoformat(lg["data_fim"])
    ]  # fmt: skip
    candidatas = vigentes or legislaturas
    return max(candidatas, key=lambda lg: lg["data_inicio"]) if candidatas else None


def em_exercicio(mandato: dict, hoje: date) -> bool:
    inicio = mandato.get("data_inicio_mandato")
    fim = mandato.get("data_fim_mandato")
    if inicio and date.fromisoformat(inicio) > hoje:
        return False
    return not fim or date.fromisoformat(fim) >= hoje


def ler_autoria(texto: str) -> tuple[str, int, int] | None:
    """'Autoria: Fulana - Requerimento nº 324 de 2026' -> ('Requerimento', 324, 2026)."""
    achado = AUTORIA.search(texto or "")
    if not achado:
        return None
    return achado.group("tipo").strip(), int(achado.group("numero")), int(achado.group("ano"))


def ler_registro(texto: str) -> tuple[str, str | None]:
    """Matéria e resultado a partir do texto do registro de votação."""
    achado = REGISTRO.search(texto or "")
    if not achado:
        return (texto or "").strip()[:300], None
    resultado = achado.group("resultado")
    return achado.group("materia").strip(), resultado.strip() if resultado else None


def _data(valor: str | None) -> str | None:
    return valor[:10] if valor else None


def coletar_votacoes(sapl: "Sapl", anos: set[int], parlamentares: set[int]) -> dict:
    """Votações nominais do período e os votos de quem está no cargo hoje."""
    registros = {}
    for ano in sorted(anos):
        for r in sapl.todos("sessao/registrovotacao/", data_hora__year=ano):
            registros[r["id"]] = r
    votos = []
    if registros:
        for ano in sorted(anos):
            for v in sapl.todos("sessao/votoparlamentar/", data_hora__year=ano):
                if v.get("votacao") in registros and v.get("parlamentar") in parlamentares:
                    votos.append(
                        {
                            "votacao": str(v["votacao"]),
                            "parlamentar": str(v["parlamentar"]),
                            "voto": (v.get("voto") or "").strip()[:30],
                        }
                    )
    com_voto = {v["votacao"] for v in votos}
    votacoes = []
    for id_, r in registros.items():
        if str(id_) not in com_voto:  # votação simbólica: ninguém votou nominalmente
            continue
        materia, resultado = ler_registro(r.get("__str__", ""))
        votacoes.append(
            {
                "id_externo": str(id_),
                "materia": materia,
                "resultado": resultado,
                "sim": r.get("numero_votos_sim") or 0,
                "nao": r.get("numero_votos_nao") or 0,
                "abstencoes": r.get("numero_abstencoes") or 0,
                "data": _data(r.get("data_hora")),
                "materia_id": r.get("materia"),
            }
        )
    return {"votacoes": votacoes, "votos": votos}


def coletar_presenca(
    sapl: "Sapl", anos: set[int], hoje: date, mandatos: dict[int, tuple[str | None, str | None]]
) -> dict[int, tuple[int | None, int | None]]:
    """Para cada parlamentar: (sessões no período durante o mandato, presenças). Contam só
    as sessões com alguma presença registrada, porque nem toda sessão tem a lista lançada.
    O filtro de ano da lista de presença é ignorado pela API; o de parlamentar funciona."""
    datas = {}
    for ano in sorted(anos):
        for sessao in sapl.todos("sessao/sessaoplenaria/", data_inicio__year=ano):
            if sessao.get("data_inicio") and sessao["data_inicio"] <= hoje.isoformat():
                datas[sessao["id"]] = sessao["data_inicio"]
    presentes: dict[int, set[int]] = {}
    for parlamentar in mandatos:
        presentes[parlamentar] = {
            p["sessao_plenaria"]
            for p in sapl.todos("sessao/sessaoplenariapresenca/", parlamentar=parlamentar)
            if p.get("sessao_plenaria") in datas
        }
    registradas = set().union(*presentes.values()) if presentes else set()
    if not registradas:
        return {p: (None, None) for p in mandatos}
    resultado = {}
    for parlamentar, (inicio, fim) in mandatos.items():
        no_mandato = {
            s for s in registradas
            if (not inicio or datas[s] >= inicio) and (not fim or datas[s] <= fim)
        }  # fmt: skip
        resultado[parlamentar] = (len(no_mandato), len(presentes[parlamentar] & no_mandato))
    return resultado


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


def tipo_parlamentar(tipos: list[dict]) -> int:
    """Id do tipo de autor "Parlamentar". Costuma ser 1, mas cada instalação numera do seu
    jeito (na Assembleia de Roraima, 1 é "Bloco Parlamentar")."""
    for tipo in tipos:
        if comum.chave_nome(tipo.get("descricao")) == "PARLAMENTAR":
            return tipo["id"]
    return 1


def coletar(base: str, hoje: date) -> dict | None:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    with comum.criar_cliente() as client:
        sapl = Sapl(base, client)
        legislatura = legislatura_atual(sapl.todos("parlamentares/legislatura/"), hoje)
        if legislatura is None:
            return None
        mandatos = sapl.todos("parlamentares/mandato/", legislatura=legislatura["id"])
        partidos = {p["id"]: p["sigla"] for p in sapl.todos("parlamentares/partido/")}
        filiacoes = sapl.todos("parlamentares/filiacao/")
        autores = {
            a["object_id"]: a["id"]
            for a in sapl.todos("base/autor/", tipo=tipo_parlamentar(sapl.todos("base/tipoautor/")))
            if a.get("object_id") is not None
        }
        anos = {hoje.year, hoje.year - 1}
        vereadores = []
        for parlamentar_id in sorted({m["parlamentar"] for m in mandatos}):
            dados = sapl.get(f"parlamentares/parlamentar/{parlamentar_id}/")
            dos_mandatos = [m for m in mandatos if m["parlamentar"] == parlamentar_id]
            atual = [
                f
                for f in filiacoes
                if f["parlamentar"] == parlamentar_id and not f.get("data_desfiliacao")
            ]
            contagem: dict[str, int] = {}
            projetos = []
            if parlamentar_id in autores:
                for autoria in sapl.todos("materia/autoria/", autor=autores[parlamentar_id]):
                    lida = ler_autoria(autoria.get("__str__", ""))
                    if not lida or lida[2] not in anos:
                        continue
                    tipo = lida[0]
                    contagem[tipo] = contagem.get(tipo, 0) + 1
                    if TIPOS_PROJETO.search(tipo):
                        materia = sapl.get(f"materia/materialegislativa/{autoria['materia']}/")
                        projetos.append(
                            {
                                "id_externo": str(materia["id"]),
                                "tipo": tipo,
                                "numero": materia.get("numero"),
                                "ano": materia.get("ano") or lida[2],
                                "ementa": " ".join((materia.get("ementa") or "").split()),
                                "data_apresentacao": materia.get("data_apresentacao"),
                                "em_tramitacao": materia.get("em_tramitacao"),
                                "primeiro_autor": bool(autoria.get("primeiro_autor")),
                                "url": base.rstrip("/") + f"/materia/{materia['id']}",
                            }
                        )
            vereadores.append(
                {
                    "id_externo": str(parlamentar_id),
                    "nome": (
                        dados.get("nome_parlamentar") or dados.get("nome_completo") or ""
                    ).strip(),
                    "nome_completo": (dados.get("nome_completo") or "").strip() or None,
                    "partido": partidos.get(atual[-1]["partido"]) if atual else None,
                    "foto_url": _https(dados.get("fotografia")),
                    "email": (dados.get("email") or "").strip() or None,
                    "telefone": (
                        dados.get("telefone_celular") or dados.get("telefone") or ""
                    ).strip()
                    or None,
                    "titular": any(m.get("titular") for m in dos_mandatos),
                    "em_exercicio": any(em_exercicio(m, hoje) for m in dos_mandatos),
                    "inicio": min(
                        (
                            m["data_inicio_mandato"]
                            for m in dos_mandatos
                            if m.get("data_inicio_mandato")
                        ),
                        default=None,
                    ),
                    "fim": max(
                        (m["data_fim_mandato"] for m in dos_mandatos if m.get("data_fim_mandato")),
                        default=None,
                    ),
                    "proposicoes_por_tipo": contagem,
                    "projetos": projetos,
                }
            )
        ids = {int(v["id_externo"]) for v in vereadores}
        votacoes = coletar_votacoes(sapl, anos, ids)
        presenca = coletar_presenca(
            sapl, anos, hoje, {int(v["id_externo"]): (v["inicio"], v["fim"]) for v in vereadores}
        )
        for v in vereadores:
            v["sessoes"], v["presencas"] = presenca[int(v["id_externo"])]
    return {"base": base, "legislatura": legislatura, "vereadores": vereadores, **votacoes}


def gravar(session: Session, ibge: str | None, camara: dict, uf: str | None = None) -> int:
    """Substitui os parlamentares e projetos da casa e liga cada um ao eleito do TSE.
    Com `ibge`, é a câmara da cidade; sem, é a assembleia legislativa de `uf`."""
    if ibge:
        uf = session.scalar(select(Municipio.uf).where(Municipio.ibge == ibge))
        filtro = [Candidatura.municipio_ibge == ibge, Candidatura.cargo == "VEREADOR"]
        anteriores = MandatoLocal.municipio_ibge == ibge
    else:
        cargos = ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")
        ultima = session.scalar(
            select(func.max(Candidatura.ano_eleicao)).where(
                Candidatura.uf == uf, Candidatura.cargo.in_(cargos)
            )
        )
        filtro = [
            Candidatura.uf == uf,
            Candidatura.cargo.in_(cargos),
            Candidatura.ano_eleicao == ultima,
        ]
        anteriores = (MandatoLocal.casa == "assembleia") & (MandatoLocal.uf == uf)
    eleitos = session.execute(
        select(Candidatura.id, Candidatura.nome_urna, Candidatura.nome).where(
            *filtro, Candidatura.situacao_turno.like("ELEITO%")
        )
    ).all()
    nomes_eleitos = [(id_, nome) for id_, urna, civil in eleitos for nome in (urna, civil)]

    def candidatura(v: dict) -> int | None:
        return casar_nome([v["nome"], v["nome_completo"]], nomes_eleitos)

    session.execute(delete(MandatoLocal).where(anteriores))
    casa = "camara" if ibge else "assembleia"
    session.execute(
        delete(VotacaoLocal).where(
            VotacaoLocal.municipio_ibge == ibge
            if ibge
            else (VotacaoLocal.casa == "assembleia") & (VotacaoLocal.uf == uf)
        )
    )
    mandato_por_parlamentar: dict[str, int] = {}
    for v in camara["vereadores"]:
        linha = {k: val for k, val in v.items() if k not in ("projetos", "gastos")}
        for campo in ("inicio", "fim"):
            linha[campo] = date.fromisoformat(linha[campo]) if linha[campo] else None
        mandato_id = session.execute(
            insert(MandatoLocal)
            .values(
                **linha,
                casa=casa,
                uf=uf,
                municipio_ibge=ibge,
                candidatura_id=candidatura(v),
                sapl_url=camara["base"],
            )
            .returning(MandatoLocal.id)
        ).scalar_one()
        mandato_por_parlamentar[v["id_externo"]] = mandato_id
        gastos = [{**g, "mandato_id": mandato_id} for g in v.get("gastos", [])]
        if gastos:
            session.execute(insert(GastoLocal), gastos)
        for p in v["projetos"]:
            session.execute(
                insert(ProjetoLocal)
                .values(
                    **{
                        **p,
                        "data_apresentacao": date.fromisoformat(p["data_apresentacao"])
                        if p["data_apresentacao"]
                        else None,
                    },
                    municipio_ibge=ibge,
                    mandato_id=mandato_id,
                )
                .on_conflict_do_nothing()
            )
    votacao_por_externo: dict[str, int] = {}
    for votacao in camara.get("votacoes", []):
        materia_id = votacao.get("materia_id")
        votacao_por_externo[votacao["id_externo"]] = session.execute(
            insert(VotacaoLocal)
            .values(
                **{k: v for k, v in votacao.items() if k not in ("materia_id", "data")},
                data=date.fromisoformat(votacao["data"]) if votacao["data"] else None,
                url=camara["base"].rstrip("/") + f"/materia/{materia_id}" if materia_id else None,
                casa=casa,
                uf=uf,
                municipio_ibge=ibge,
            )
            .returning(VotacaoLocal.id)
        ).scalar_one()
    votos = [
        {
            "votacao_id": votacao_por_externo[v["votacao"]],
            "mandato_id": mandato_por_parlamentar[v["parlamentar"]],
            "voto": v["voto"],
        }
        for v in camara.get("votos", [])
        if v["votacao"] in votacao_por_externo and v["parlamentar"] in mandato_por_parlamentar
    ]
    for inicio in range(0, len(votos), 5000):
        session.execute(insert(VotoLocal).on_conflict_do_nothing(), votos[inicio : inicio + 5000])
    return len(camara["vereadores"])


def executar(
    limite: int | None = None, trabalhadores: int = 8, ufs: list[str] | None = None
) -> int:
    camaras = [
        (c["municipio_ibge"], c["url"])
        for c in catalogo.ler()
        if c["tipo"] == "sapl" and (not ufs or c["uf"] in ufs)
    ]
    camaras = camaras[:limite] if limite else camaras
    hoje = date.today()
    total, falhas = 0, 0

    def uma(item: tuple[str, str]) -> int:
        ibge, base = item
        try:
            camara = coletar(base, hoje)
            if not camara:
                return 0
            with SessionLocal() as session:
                total = gravar(session, ibge, camara)
                session.commit()
            return total
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {base}: {erro.__class__.__name__}: {str(erro)[:120]}")
            return -1

    with ThreadPoolExecutor(max_workers=trabalhadores) as pool:
        for resultado in pool.map(uma, camaras):
            if resultado < 0:
                falhas += 1
            else:
                total += resultado
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="SAPL das câmaras do catálogo data/canais_oficiais.csv",
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(f"{len(camaras)} câmaras, {falhas} com falha, {total} vereadores")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--limite", type=int, help="Só as N primeiras câmaras (teste)")
    parser.add_argument("--uf", nargs="*", help="Só as câmaras destes estados")
    args = parser.parse_args()
    executar(args.limite, ufs=[u.upper() for u in args.uf] if args.uf else None)
