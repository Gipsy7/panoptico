"""Cruzamentos por pessoa: sanções, serviço federal, carreira eleitoral e o feed de eventos.

Tudo parte da pessoa pública única e só usa vínculos publicáveis (fortes ou revisados). Nada
de CPF, título ou data de nascimento sai daqui: a `regra` informa só COMO a ligação foi feita.
"""

from datetime import UTC, date, datetime
from xml.etree import ElementTree as ET

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CpgfPortadorMes,
    Evento,
    FonteIngestao,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    ServidorFederal,
    ViagemFederalAno,
)
from app.services import pessoas as svc_pessoas
from app.services import tse
from app.services.pessoas import publicavel

TIPOS_SANCAO = ("sancao", "tcu_contas_irregulares", "tcu_inabilitacao")

# Texto curto, em linguagem do dia a dia, para cada regra de ligação.
REGRAS = {
    "cpf": "ligado pelo CPF",
    "cpf_parcial_nome": "ligado por parte do CPF (o resto é ocultado pela fonte) e pelo nome",
    "titulo": "ligado pelo título de eleitor",
    "tse": "ligado pelo cadastro do TSE",
    "origem": "ligado pelo próprio registro da fonte",
    "nome_nascimento": "ligado pelo nome e pela data de nascimento",
    "nome_parlamentar": "ligado pelo nome parlamentar, único no cadastro da Casa",
    "nome_exato_casa": (
        "ligado pelo nome, igual ao do eleito no TSE e único entre os eleitos da Casa"
    ),
}

# Recorte do TSE (ingestion/fontes.toml: tse_candidaturas e tse_bens).
ANOS_CANDIDATURAS = [1994, 1998, 2002, 2006, 2010, 2014, 2016, 2018, 2020, 2022, 2024, 2026]
ANOS_BENS = [2018, 2022, 2024]
RECORTE_CARREIRA = (
    "Candidaturas de 2018, 2022, 2024 e 2026 completas para eleitos e parlamentares; "
    "1994 a 2020 só de quem já está na base (o TSE não publica o cadastro de candidaturas "
    "de antes de 1994). Bens declarados só das eleições de 2018, 2022 "
    "e 2024; votos só quando a fonte os traz."
)

URL_SANCOES = "https://portaldatransparencia.gov.br/sancoes"
FONTES_SERVICO = ("cgu_servidores", "cgu_viagens", "cgu_viagens_cne", "cgu_cpgf")
URL_PORTAL = "https://portaldatransparencia.gov.br/"


def _texto_regra(regra: str) -> str:
    return REGRAS.get(regra, "ligado por revisão manual")


def _atualizado(session: Session, fontes) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(fontes), FonteIngestao.status == "ok"
        )
    )


def _existe(session: Session, pessoa_id: int) -> bool:
    return session.get(Pessoa, pessoa_id) is not None


def sancoes(session: Session, pessoa_id: int) -> dict | None:
    if not _existe(session, pessoa_id):
        return None
    linhas = session.execute(
        select(Evento, PessoaVinculo.regra)
        .join(PessoaVinculo, PessoaVinculo.id == Evento.vinculo_id)
        .where(Evento.pessoa_id == pessoa_id, Evento.tipo.in_(TIPOS_SANCAO), publicavel())
        .order_by(Evento.data.desc().nulls_last(), Evento.id)
    ).all()
    itens = [
        {
            "data": e.data,
            "tipo": e.tipo,
            "descricao": e.descricao,
            "orgao": e.orgao,
            "numero_processo": e.numero_processo,
            "situacao": e.situacao,
            "fonte": e.fonte,
            "fonte_url": e.fonte_url,
            "regra": regra,
            "ligacao": _texto_regra(regra),
        }
        for e, regra in linhas
    ]
    fontes = {e.fonte for e, _ in linhas} or {"cgu_ceis", "cgu_cnep", "cgu_ceaf"}
    return {
        "pessoa_id": pessoa_id,
        "itens": itens,
        "fonte_nome": "Portal da Transparência (CGU) e Tribunal de Contas da União",
        "fonte_url": URL_SANCOES,
        "atualizado_em": _atualizado(session, fontes),
    }


def _ids_publicaveis(session: Session, pessoa_id: int, fonte: str) -> dict[str, str]:
    """id_externo -> regra dos vínculos publicáveis da pessoa nesta fonte."""
    return dict(
        session.execute(
            select(PessoaVinculo.id_externo, PessoaVinculo.regra).where(
                PessoaVinculo.pessoa_id == pessoa_id, PessoaVinculo.fonte == fonte, publicavel()
            )
        ).all()
    )


def _vinculo_publicavel(fonte: str, id_externo):
    """A linha só entra na média se o vínculo dela com a pessoa também é publicável."""
    return (
        select(PessoaVinculo.id)
        .where(PessoaVinculo.fonte == fonte, PessoaVinculo.id_externo == id_externo, publicavel())
        .exists()
    )


def _media_da_casa(session: Session) -> dict:
    """Viagens e cartão por ano, divididos pelos parlamentares federais em exercício (quem
    não tem registro entra com zero)."""
    em_exercicio = list(
        session.scalars(select(Parlamentar).where(Parlamentar.em_exercicio.is_(True)))
    )
    n = len(em_exercicio)
    if n == 0:
        return {"parlamentares": 0, "viagens": {}, "viagens_valor": {}, "cartao": {}}
    chaves = [f"{p.casa}:{p.id_externo}" for p in em_exercicio]
    ids = select(PessoaVinculo.pessoa_id).where(
        PessoaVinculo.fonte == "parlamentar", PessoaVinculo.id_externo.in_(chaves), publicavel()
    )
    viagens = session.execute(
        select(
            ViagemFederalAno.ano,
            func.sum(ViagemFederalAno.viagens),
            func.sum(
                ViagemFederalAno.diarias + ViagemFederalAno.passagens + ViagemFederalAno.outros
            ),
        )
        .where(
            ViagemFederalAno.pessoa_id.in_(ids),
            _vinculo_publicavel(
                "cgu_viagens",
                func.concat(ViagemFederalAno.ano, ":", ViagemFederalAno.pessoa_id),
            ),
        )
        .group_by(ViagemFederalAno.ano)
    ).all()
    cartao = session.execute(
        select(CpgfPortadorMes.ano, func.sum(CpgfPortadorMes.total))
        .where(
            CpgfPortadorMes.pessoa_id.in_(ids),
            _vinculo_publicavel(
                "cgu_cpgf",
                func.concat(
                    CpgfPortadorMes.ano,
                    ":",
                    CpgfPortadorMes.pessoa_id,
                    ":",
                    func.left(CpgfPortadorMes.orgao, 60),
                ),
            ),
        )
        .group_by(CpgfPortadorMes.ano)
    ).all()
    return {
        "parlamentares": n,
        "viagens": {a: round(float(q) / n, 2) for a, q, _ in viagens},
        "viagens_valor": {a: round(float(v) / n, 2) for a, _, v in viagens},
        "cartao": {a: round(float(t) / n, 2) for a, t in cartao},
    }


def servico_federal(session: Session, pessoa_id: int) -> dict | None:
    if not _existe(session, pessoa_id):
        return None
    vinc_servidor = {
        **_ids_publicaveis(session, pessoa_id, "cgu_servidores"),
        **_ids_publicaveis(session, pessoa_id, "cgu_viagens_cne"),
    }
    cargos = [
        s
        for s in session.scalars(
            select(ServidorFederal)
            .where(ServidorFederal.pessoa_id == pessoa_id)
            .order_by(ServidorFederal.ultimo_mes.desc(), ServidorFederal.id)
        )
        if s.id_externo in vinc_servidor
    ]
    recente = session.scalar(
        select(func.max(ServidorFederal.ultimo_mes)).where(ServidorFederal.origem == "siape")
    )
    vinc_viagem = _ids_publicaveis(session, pessoa_id, "cgu_viagens")
    viagens = [
        v
        for v in session.scalars(
            select(ViagemFederalAno)
            .where(ViagemFederalAno.pessoa_id == pessoa_id)
            .order_by(ViagemFederalAno.ano.desc())
        )
        if f"{v.ano}:{v.pessoa_id}" in vinc_viagem
    ]
    vinc_cartao = _ids_publicaveis(session, pessoa_id, "cgu_cpgf")
    cartao_bruto = session.execute(
        select(
            CpgfPortadorMes.ano,
            CpgfPortadorMes.orgao,
            func.sum(CpgfPortadorMes.transacoes),
            func.sum(CpgfPortadorMes.total),
            func.sum(CpgfPortadorMes.saques),
        )
        .where(CpgfPortadorMes.pessoa_id == pessoa_id)
        .group_by(CpgfPortadorMes.ano, CpgfPortadorMes.orgao)
        .order_by(CpgfPortadorMes.ano.desc(), CpgfPortadorMes.orgao)
    ).all()
    cartao = [
        {"ano": a, "orgao": o, "transacoes": int(n), "total": float(t), "saques": float(s)}
        for a, o, n, t, s in cartao_bruto
        if f"{a}:{pessoa_id}:{o[:60]}" in vinc_cartao
    ]
    regras = {*vinc_servidor.values(), *vinc_viagem.values(), *vinc_cartao.values()}
    regra = next(iter(regras)) if len(regras) == 1 else ("cpf_parcial_nome" if regras else None)
    media = _media_da_casa(session) if (viagens or cartao) else None
    return {
        "pessoa_id": pessoa_id,
        "regra": regra,
        "ligacao": _texto_regra(regra) if regra else None,
        "cargos": [
            {
                "funcao": s.funcao,
                "sigla": s.sigla,
                "nivel": s.nivel,
                "orgao": s.orgao,
                "origem": "viagens" if s.origem == "viagens" else "cadastro de servidores",
                "primeiro_mes": s.primeiro_mes,
                "ultimo_mes": s.ultimo_mes,
                "consta_no_cadastro_mais_recente": bool(
                    s.origem == "siape" and recente and s.ultimo_mes >= recente
                ),
            }
            for s in cargos
        ],
        "viagens_por_ano": [
            {
                "ano": v.ano,
                "viagens": v.viagens,
                "diarias": float(v.diarias),
                "passagens": float(v.passagens),
                "outros": float(v.outros),
                "devolucao": float(v.devolucao),
                "ultima_viagem": v.ultima_viagem,
                "media_casa_viagens": media["viagens"].get(v.ano, 0) if media else None,
                "media_casa_valor": media["viagens_valor"].get(v.ano, 0) if media else None,
            }
            for v in viagens
        ],
        "cartao_por_ano_e_orgao": [
            {**c, "media_casa_total": media["cartao"].get(c["ano"], 0) if media else None}
            for c in cartao
        ],
        "media_da_casa": (
            {
                "parlamentares_em_exercicio": media["parlamentares"],
                "descricao": (
                    "Média entre deputados e senadores em exercício; quem não tem registro "
                    "entra com zero. Cartão: média do total por ano, somando os órgãos."
                ),
            }
            if media
            else None
        ),
        "fonte_nome": "Portal da Transparência (CGU): servidores, viagens e cartão de pagamento",
        "fonte_url": URL_PORTAL,
        "atualizado_em": _atualizado(session, FONTES_SERVICO),
    }


def carreira(session: Session, pessoa_id: int) -> dict | None:
    if not _existe(session, pessoa_id):
        return None
    vinculos = [v for v in svc_pessoas._vinculos(session, pessoa_id) if v.fonte == "candidatura"]
    regras = {v.id_externo: v.regra for v in vinculos}
    itens = []
    for c in sorted(
        svc_pessoas._candidaturas(session, vinculos), key=lambda c: (-c.ano_eleicao, c.cargo)
    ):
        regra = regras.get(f"{c.ano_eleicao}:{c.sq_candidato}", "")
        tem_bens = tse._tem_bens(session, c.id)
        itens.append(
            {
                "ano": c.ano_eleicao,
                "cargo": c.cargo.capitalize(),
                "uf": c.uf,
                "unidade": c.unidade,
                "municipio": c.unidade if c.municipio_ibge else None,
                "partido": c.partido,
                "numero": c.numero,
                "situacao": tse._situacao(c.situacao_turno),
                "eleito": (c.situacao_turno or "").startswith("ELEITO"),
                "votos": c.votos,
                "bens_total": float(tse._total_bens(session, c.id)) if tem_bens else None,
                "bens_declarados": tem_bens,
                "fonte_url": tse.URL_CANDIDATOS.format(ano=c.ano_eleicao),
                "regra": regra,
                "ligacao": _texto_regra(regra),
            }
        )
    return {
        "pessoa_id": pessoa_id,
        "itens": itens,
        "recorte": {
            "texto": RECORTE_CARREIRA,
            "anos_candidaturas": ANOS_CANDIDATURAS,
            "anos_bens": ANOS_BENS,
        },
        "fonte_nome": tse.FONTE_NOME,
        "fonte_url": tse.FONTE_URL,
        "atualizado_em": tse._atualizado_em(session),
    }


# ---- Feed Atom ------------------------------------------------------------------------

ATOM = "http://www.w3.org/2005/Atom"
TITULOS = {
    "eleito": "Eleição",
    "sancao": "Sanção registrada",
    "tcu_contas_irregulares": "Contas julgadas irregulares pelo TCU",
    "tcu_inabilitacao": "Inabilitação registrada pelo TCU",
    "cargo_federal": "Cargo no governo federal",
    "viagem_federal": "Viagens a serviço",
    "cartao_corporativo": "Cartão de pagamento do governo",
}
LIMITE_FEED = 50


def _titulo(item: dict) -> str:
    base = TITULOS.get(item["tipo"], item["tipo"].replace("_", " ").capitalize())
    return f"{base}, {item['orgao']}" if item.get("orgao") else base


def feed_atom(session: Session, pessoa_id: int, url_feed: str, url_perfil: str) -> bytes | None:
    """Atom 1.0 com os eventos publicáveis e as eleições (mais novos primeiro, até 50)."""
    resultado = svc_pessoas.eventos(session, pessoa_id)
    registro = session.get(Pessoa, pessoa_id)
    if resultado is None or registro is None:
        return None
    itens = resultado["itens"][:LIMITE_FEED]
    datas = [i["data"] for i in itens if i["data"]] + [
        i["conferido_em"] for i in itens if i["conferido_em"]
    ]
    atualizado = max(datas) if datas else date.today()

    def iso(d: date) -> str:
        return datetime(d.year, d.month, d.day, tzinfo=UTC).isoformat()

    raiz = ET.Element(f"{{{ATOM}}}feed")
    ET.SubElement(
        raiz, f"{{{ATOM}}}title"
    ).text = f"Panóptico: fatos oficiais sobre {registro.nome}"
    ET.SubElement(raiz, f"{{{ATOM}}}id").text = url_feed
    ET.SubElement(raiz, f"{{{ATOM}}}updated").text = iso(atualizado)
    ET.SubElement(raiz, f"{{{ATOM}}}link", rel="self", href=url_feed)
    ET.SubElement(raiz, f"{{{ATOM}}}link", rel="alternate", href=url_perfil)
    ET.SubElement(
        raiz, f"{{{ATOM}}}subtitle"
    ).text = "Registros de fontes oficiais ligados a esta pessoa, com link da fonte."
    for n, i in enumerate(itens):
        e = ET.SubElement(raiz, f"{{{ATOM}}}entry")
        ET.SubElement(e, f"{{{ATOM}}}title").text = _titulo(i)
        link = i["fonte_url"] or url_perfil
        ET.SubElement(
            e, f"{{{ATOM}}}id"
        ).text = f"{url_feed}#{n}-{i['tipo']}-{i['data'] or 'sem-data'}"
        ET.SubElement(e, f"{{{ATOM}}}updated").text = iso(
            i["data"] or i["conferido_em"] or atualizado
        )
        ET.SubElement(e, f"{{{ATOM}}}link", rel="alternate", href=link)
        fonte = f" Fonte: {i['orgao']}." if i.get("orgao") else ""
        data = f" Data: {i['data']:%d/%m/%Y}." if i["data"] else " Sem data informada."
        ET.SubElement(e, f"{{{ATOM}}}summary").text = f"{i['descricao']}{data}{fonte}"
    return ET.tostring(raiz, encoding="utf-8", xml_declaration=True)
