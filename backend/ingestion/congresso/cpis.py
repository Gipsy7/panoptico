"""CPIs (Câmara e Senado) e CPMIs (Congresso Nacional) criadas desde 2019: a comissão, o
objeto, as datas, quem a presidiu, quem foi relator e quem foi membro, e o link do relatório
final quando a casa o publica. A participação de cada parlamentar vira um evento da linha do
tempo (fato oficial, sem juízo); indiciamentos NÃO entram aqui (ver cpi_indiciamentos.py).

Fontes, todas das próprias casas:

- Câmara (CPIs): arquivos em lote dos Dados Abertos, `orgaos.json` (tipo 4, Comissão
  Parlamentar de Inquérito) e `orgaosDeputados-L{legislatura}.json` (membros, com cargo e
  datas). O relatório vem das tramitações do requerimento de criação (RCP): a que apresenta
  o "relatório final" ou o "relatório do relator" na própria CPI. Nem toda CPI tem um.
- Senado e Congresso (CPIs e CPMIs): a API lista as comissões de cada senador (por
  legislatura), que é a única forma de achar as já encerradas (as listas de colegiados só
  trazem as em atividade). Presidente, relator, membros e o link do relatório final saem das
  páginas oficiais da comissão (legis.senado.leg.br/comissoes), que a API não expõe. Os
  membros são a última posição de cada vaga: quem saiu no meio do caminho pode não constar.

O id do parlamentar é o oficial da casa (Câmara: `deputados/{id}`; Senado: código do
parlamentar; as CPMIs trazem os dois, pelo link do perfil). Liga-se à pessoa pelo cadastro
de parlamentares (origem) ou, para quem já saiu, pelo nome parlamentar exato e único entre os
eleitos, com a mesma UF (nome_parlamentar). Sem ligação, a participação fica na tabela mas
não vira evento.
"""

import argparse
import html
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import String, delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    Cpi,
    CpiParticipacao,
    Evento,
    FonteIngestao,
    Parlamentar,
    PessoaVinculo,
)
from ingestion import comum

FONTE = "cpis"
TIPO_EVENTO = "cpi"
DESDE = "2019-01-01"
PAUSA = 0.2
API_CD = "https://dadosabertos.camara.leg.br/api/v2"
URL_CD_ORGAOS = "https://dadosabertos.camara.leg.br/arquivos/orgaos/json/orgaos.json"
URL_CD_MEMBROS = (
    "https://dadosabertos.camara.leg.br/arquivos/orgaosDeputados/json/orgaosDeputados-L{leg}.json"
)
URL_SF = "https://legis.senado.leg.br/dadosabertos"
URL_SF_COMISSAO = "https://legis.senado.leg.br/comissoes/comissao?codcol={codigo}"
URL_SF_COMPOSICAO = "https://legis.senado.leg.br/comissoes/composicao_comissao?codcol={codigo}"
PRIMEIRA_LEGISLATURA = 56  # 2019-2023

# Do mais importante ao menos: o evento usa o papel de maior peso de cada pessoa.
PESO = {
    "Presidente": 0,
    "Relator": 1,
    "Relatora": 1,
    "Vice-presidente": 2,
    "Titular": 3,
    "Suplente": 4,
}
CASA_TEXTO = {
    "camara": ("Câmara dos Deputados", "comissão parlamentar de inquérito da Câmara dos Deputados"),
    "senado": ("Senado Federal", "comissão parlamentar de inquérito do Senado Federal"),
    "congresso": (
        "Congresso Nacional",
        "comissão parlamentar mista de inquérito do Congresso Nacional",
    ),
}
RELATORIO_CD = re.compile(
    r"relat[óo]rio\s+final|relat[óo]rio\s+do\s+relator|parecer\s+do\s+relator", re.I
)
NAO_RELATORIO = re.compile(r"dilig[êe]ncia|viagem|visita|parcial|requer", re.I)


# --- utilidades -----------------------------------------------------------------------


def _lista(valor: Any) -> list:
    """O Senado devolve objeto, e não lista, quando há um item só."""
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def _data(valor: str | None) -> date | None:
    valor = (valor or "").strip()[:10]
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho)).split())


def cargo_normalizado(bruto: str | None) -> str:
    """'1º VICE-PRESIDENTE' -> 'Vice-presidente'; 'RELATORA' -> 'Relatora'; resto como veio."""
    cru = " ".join((bruto or "").split())
    alto = cru.upper()
    if "VICE" in alto:
        return "Vice-presidente"
    if alto.startswith("RELATOR"):
        return "Relatora" if alto.endswith("A") else "Relator"
    if alto.startswith("PRESIDENTE"):
        return "Presidente"
    return cru.capitalize()


# --- Câmara -----------------------------------------------------------------------------


def _id_final(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def orgaos_cpi_camara(orgaos: list[dict]) -> list[dict]:
    """CPIs (tipo 4) com início desde 2019. O arquivo repete órgãos antigos com ids diferentes;
    a partir de 2019 cada CPI tem um id só."""
    return [
        o
        for o in orgaos
        if o.get("codTipoOrgao") == 4 and (o.get("dataInicio") or "")[:10] >= DESDE
    ]


def relatorio_camara(tramitacoes: list[dict], sigla: str, inicio: date, fim: date) -> dict | None:
    """O relatório final (ou do relator) apresentado na própria CPI: a última tramitação do
    órgão, dentro da vida da CPI, que traz o documento. None se não houver."""
    achados = []
    for t in tramitacoes:
        data = _data(t.get("dataHora"))
        texto = " ".join(
            ((t.get("despacho") or "") + " " + (t.get("descricaoTramitacao") or "")).split()
        )
        if (
            t.get("siglaOrgao") == sigla
            and data
            and inicio <= data <= fim
            and t.get("url")
            and RELATORIO_CD.search(texto)
            and not NAO_RELATORIO.search(texto)
        ):
            achados.append({"url": t["url"], "rotulo": texto[:200], "data": str(data)})
    if not achados:
        return None
    finais = [a for a in achados if re.search(r"final", a["rotulo"], re.I)]
    return (finais or achados)[-1]


def linhas_camara(orgaos: list[dict], membros: list[dict], relatorios: dict) -> list[dict]:
    por_orgao: dict[str, list[dict]] = {}
    for m in membros:
        por_orgao.setdefault(_id_final(m["uriOrgao"]), []).append(m)
    cpis = []
    for o in orgaos:
        id_ = _id_final(o["uri"])
        rel = relatorios.get(id_)
        fim = _data(o.get("dataFim"))
        participacoes = [
            {
                "casa_parlamentar": "camara",
                "id_parlamentar": _id_final(m["uriDeputado"]),
                "nome": m["nomeDeputado"],
                "partido": m.get("siglaPartido") or None,
                "uf": m.get("siglaUF") or None,
                "cargo": cargo_normalizado(m.get("cargo")),
                "data_inicio": _data(m.get("dataInicio")),
                "data_fim": _data(m.get("dataFim")),
            }
            for m in por_orgao.get(id_, [])
        ]
        cpis.append(
            {
                "casa": "camara",
                "id_externo": id_,
                "tipo": "CPI",
                "sigla": (o.get("sigla") or "")[:60] or None,
                "nome": (o.get("apelido") or o.get("nomePublicacao") or o["nome"])[:300],
                "objeto": " ".join(o["nome"].split()),
                "data_criacao": _data(o.get("dataInicio")),
                "data_instalacao": _data(o.get("dataInstalacao")),
                "data_fim": fim,
                "situacao": (o.get("descricaoSituacao") or "").strip()[:80]
                or ("Encerrada" if fim else "Em funcionamento"),
                "relatorio_url": rel["url"] if rel else None,
                "relatorio_rotulo": rel["rotulo"] if rel else None,
                "fonte_url": o["uri"],
                "participacoes": participacoes,
            }
        )
    return cpis


# --- Senado e Congresso -------------------------------------------------------------------

BLOCO_MEMBRO = re.compile(
    r'id="bloco_membro_\d+">\s*'
    r'(?:<div class="sf-atv-cmss-composicao-membro__titulo">(?P<cargo>[^<]*)</div>)?\s*'
    r'<a href="(?P<href>[^"]+)">(?:(?!bloco_membro_).)*?<span>(?P<nome>[^<]*)</span>\s*</div>\s*'
    r"<div>\((?P<sigla>[^)]*)\)</div>",
    re.S,
)
CABECALHO_VAGA = re.compile(r'composicao-titulo-tipo-vaga">\s*(Titulares|Suplentes)')
HREF_SENADOR = re.compile(r"/senadores/senador/-/perfil/(\d+)")
HREF_DEPUTADO = re.compile(r"camara\.leg\.br/deputados/(\d+)")


def membros_do_html(pagina: str) -> list[dict]:
    """Presidente, vice-presidentes, relator e as vagas de titular e suplente da página de
    composição da comissão. O id vem do link do perfil (Senado) ou do deputado (Câmara)."""
    marcas = sorted(
        [(m.start(), "membro", m) for m in BLOCO_MEMBRO.finditer(pagina)]
        + [(m.start(), "vaga", m) for m in CABECALHO_VAGA.finditer(pagina)],
        key=lambda x: x[0],
    )
    vaga = None
    linhas = []
    for _, tipo, m in marcas:
        if tipo == "vaga":
            vaga = "Titular" if m.group(1) == "Titulares" else "Suplente"
            continue
        href = html.unescape(m.group("href"))
        sen, dep = HREF_SENADOR.search(href), HREF_DEPUTADO.search(href)
        if not (sen or dep):
            continue  # vaga sem parlamentar
        partido, _, uf = html.unescape(m.group("sigla")).partition("/")
        cargo = m.group("cargo")
        linhas.append(
            {
                "casa_parlamentar": "senado" if sen else "camara",
                "id_parlamentar": (sen or dep).group(1),
                "nome": re.sub(
                    r"^(Sen|Dep)\.\s*", "", " ".join(html.unescape(m.group("nome")).split())
                ),
                "partido": partido.strip()[:30] or None,
                "uf": uf.strip()[:2] or None,
                "cargo": cargo_normalizado(cargo) if cargo else (vaga or "Titular"),
                "data_inicio": None,
                "data_fim": None,
            }
        )
    return linhas


def dados_da_pagina(pagina: str) -> dict:
    """Situação, finalidade, eventos (datas) e o link do relatório final da página da comissão."""
    campos = {
        _texto(k): _texto(v)
        for k, v in re.findall(r"<dt>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", pagina, re.S)
    }
    eventos = [
        (_data(d), _texto(rotulo))
        for d, rotulo in re.findall(
            r"<strong>(\d\d/\d\d/\d{4})</strong>:\s*<span>(.*?)</span>", pagina, re.S
        )
    ]
    relatorio = None
    for href, rotulo in re.findall(
        r'<a[^>]*href="([^"]+)"[^>]*>\s*<div[^>]*>\s*<b>\s*([^<]*Relat[óo]rio[^<]*?)\s*</b>',
        pagina,
    ):
        item = (html.unescape(href), _texto(rotulo))
        if relatorio is None or (
            "final" in item[1].lower() and "final" not in relatorio[1].lower()
        ):
            relatorio = item
    return {
        "situacao": campos.get("Situação atual") or None,
        "finalidade": campos.get("Finalidade") or None,
        "eventos": eventos,
        "relatorio": relatorio,
    }


def linha_senado(col: dict) -> dict | None:
    """Uma comissão do Senado/Congresso (com as duas páginas guardadas no bruto)."""
    dados = dados_da_pagina(col["comissao_html"])
    eventos = dados["eventos"]

    def primeira(*rotulos: str) -> date | None:
        return next((d for d, r in eventos if d and r in rotulos), None)

    prazos = [d for d, r in eventos if d and r.lower().startswith("prazo final")]
    criacao = primeira("Designação", "Criação")
    instalacao = primeira("Instalação")
    criacao = criacao or _data(col.get("data_inicio"))
    marco = instalacao or criacao
    if not marco or marco.isoformat() < DESDE:
        return None  # sem data, ou anterior a 2019 (só os membros atravessaram o ano)
    relatorio = dados["relatorio"]
    return {
        "casa": "congresso" if col["casa"] == "CN" else "senado",
        "id_externo": str(col["codigo"]),
        "tipo": "CPMI" if col["casa"] == "CN" else "CPI",
        "sigla": col["sigla"][:60],
        "nome": col["nome"][:300],
        "objeto": dados["finalidade"],
        "data_criacao": criacao,
        "data_instalacao": instalacao,
        "data_fim": max(prazos) if prazos else None,
        "situacao": (dados["situacao"] or "").replace("Instalac?o", "Instalação")[:80] or None,
        "relatorio_url": relatorio[0] if relatorio else None,
        "relatorio_rotulo": relatorio[1][:200] if relatorio else None,
        "fonte_url": URL_SF_COMISSAO.format(codigo=col["codigo"]),
        "participacoes": membros_do_html(col["composicao_html"]),
    }


def colegiados_da_lista(no: Any) -> list[dict]:
    """Os itens com `CodigoColegiado` de uma lista de colegiados do Senado, em qualquer nível
    de aninhamento (a resposta aninha listas dentro de objetos de um item só)."""
    if isinstance(no, list):
        return [c for item in no for c in colegiados_da_lista(item)]
    if isinstance(no, dict):
        if "CodigoColegiado" in no:
            return [no]
        return [c for item in no.values() for c in colegiados_da_lista(item)]
    return []


def comissoes_de_inquerito(lista: list[dict]) -> dict[str, dict]:
    """De uma lista de comissões de um senador (API), as CPIs e CPMIs com participação em
    2019 ou depois: código -> {codigo, sigla, nome, casa}."""
    achadas = {}
    for c in lista:
        ident = c["IdentificacaoComissao"]
        sigla, nome = ident.get("SiglaComissao") or "", ident.get("NomeComissao") or ""
        nome_baixo = nome.lower()
        inquerito = "parlamentar" in nome_baixo and "inqu" in nome_baixo
        if not (re.match(r"CPM?I", sigla.upper()) or inquerito):
            continue
        if (c.get("DataFim") or "9999")[:10] < DESDE:
            continue
        achadas[str(ident["CodigoComissao"])] = {
            "codigo": str(ident["CodigoComissao"]),
            "sigla": sigla,
            "nome": nome,
            "casa": ident.get("SiglaCasaComissao") or "SF",
        }
    return achadas


# --- ligação à pessoa -----------------------------------------------------------------------


def ligadores(session: Session) -> tuple[dict[str, int], dict[tuple[str, str], dict[int, set]]]:
    """(1) 'casa:id' -> pessoa, pelo cadastro de parlamentares em exercício;
    (2) (casa, nome) -> {pessoa: UFs}, dos parlamentares em exercício e dos eleitos para
    deputado federal e senador (nome parlamentar, nome de urna e nome civil)."""
    por_id = dict(
        session.execute(
            select(PessoaVinculo.id_externo, PessoaVinculo.pessoa_id).where(
                PessoaVinculo.fonte == "parlamentar"
            )
        ).all()
    )
    por_nome: dict[tuple[str, str], dict[int, set]] = {}

    def anotar(casa: str, nome: str | None, pessoa: int | None, uf: str | None) -> None:
        if nome and pessoa:
            chave = (casa, comum.chave_nome(nome))
            por_nome.setdefault(chave, {}).setdefault(pessoa, set()).add(uf)

    for casa, id_externo, nome, civil, uf in session.execute(
        select(
            Parlamentar.casa,
            Parlamentar.id_externo,
            Parlamentar.nome_parlamentar,
            Parlamentar.nome_civil,
            Parlamentar.uf,
        )
    ):
        pessoa = por_id.get(f"{casa}:{id_externo}")
        anotar(casa, nome, pessoa, uf)
        anotar(casa, civil, pessoa, uf)
    cargo_casa = {"DEPUTADO FEDERAL": "camara", "SENADOR": "senado"}
    chave_candidatura = Candidatura.ano_eleicao.cast(String) + ":" + Candidatura.sq_candidato
    for cargo, uf, urna, civil, pessoa in session.execute(
        select(
            Candidatura.cargo,
            Candidatura.uf,
            Candidatura.nome_urna,
            Candidatura.nome,
            PessoaVinculo.pessoa_id,
        )
        .join(
            PessoaVinculo,
            (PessoaVinculo.fonte == "candidatura")
            & (PessoaVinculo.id_externo == chave_candidatura),
        )
        .where(Candidatura.cargo.in_(list(cargo_casa)), Candidatura.situacao_turno.like("ELEITO%"))
    ):
        anotar(cargo_casa[cargo], urna, pessoa, uf)
        anotar(cargo_casa[cargo], civil, pessoa, uf)
    return por_id, por_nome


def ligar(
    p: dict,
    por_id: dict[str, int],
    por_nome: dict[tuple[str, str], dict[int, set]],
) -> tuple[int | None, str | None]:
    """(pessoa, regra). Pelo id oficial, se o parlamentar está no cadastro; senão, pelo nome
    exato e único entre os eleitos da mesma casa, desde que a UF não contradiga."""
    pessoa = por_id.get(f"{p['casa_parlamentar']}:{p['id_parlamentar']}")
    if pessoa:
        return pessoa, "origem"
    candidatos = por_nome.get((p["casa_parlamentar"], comum.chave_nome(p["nome"])), {})
    if len(candidatos) == 1:
        pessoa, ufs = next(iter(candidatos.items()))
        if not p.get("uf") or p["uf"] in ufs:
            return pessoa, "nome_parlamentar"
    return None, None


# --- eventos e carga --------------------------------------------------------------------------


def papel(cargos: list[str]) -> str:
    """'Presidente', 'Relator e vice-presidente', 'Membro titular'... o papel na comissão."""
    ordem = sorted(set(cargos), key=lambda c: PESO.get(c, 5))
    altos = [c for c in ordem if PESO.get(c, 5) < PESO["Titular"]]
    if altos:
        return " e ".join(a.lower() if i else a for i, a in enumerate(altos))
    return "Membro titular" if "Titular" in ordem else "Membro suplente"


def evento_da(cpi: dict, cargos: list[str], pessoa: int, vinculo_id: int) -> dict[str, Any]:
    orgao, tipo_texto = CASA_TEXTO[cpi["casa"]]
    objeto = " ".join((cpi["objeto"] or "").split())
    if len(objeto) > 400:
        objeto = objeto[:400].rsplit(" ", 1)[0] + "…"
    descricao = f"{papel(cargos)} na {cpi['nome']}, {tipo_texto}"
    if cpi["data_instalacao"]:
        descricao += f", instalada em {cpi['data_instalacao']:%d/%m/%Y}"
    descricao += "."
    if objeto:
        descricao += f' Finalidade, segundo a comissão: "{objeto}"'
    return {
        "pessoa_id": pessoa,
        "vinculo_id": vinculo_id,
        "id_externo": f"{cpi['casa']}:{cpi['id_externo']}:{pessoa}",
        "data": cpi["data_instalacao"] or cpi["data_criacao"],
        "tipo": TIPO_EVENTO,
        "descricao": descricao,
        "orgao": f"{orgao} – {cpi['tipo']}",
        "numero_processo": (cpi["sigla"] or "")[:40] or None,
        "situacao": cpi["situacao"],
        "fonte_url": cpi["fonte_url"],
    }


def gravar(session: Session, cpis: list[dict], ingestao_id: int | None) -> int:
    if not cpis:
        raise RuntimeError("nenhuma CPI encontrada: a fonte pode ter falhado")
    por_id, por_nome = ligadores(session)
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))  # e os eventos
    total = ligadas = eventos = 0
    vinculos: dict[str, int] = {}
    for c in cpis:
        campos = {k: v for k, v in c.items() if k != "participacoes"}
        cpi_id = session.scalar(
            pg_insert(Cpi)
            .values(**campos, ingestao_id=ingestao_id)
            .on_conflict_do_update(
                index_elements=[Cpi.casa, Cpi.id_externo],
                set_={**campos, "ingestao_id": ingestao_id},
            )
            .returning(Cpi.id)
        )
        session.execute(delete(CpiParticipacao).where(CpiParticipacao.cpi_id == cpi_id))
        por_pessoa: dict[int, tuple[list[str], int]] = {}
        for p in c["participacoes"]:
            pessoa, regra = ligar(p, por_id, por_nome)
            session.execute(
                insert(CpiParticipacao).values(**p, cpi_id=cpi_id, pessoa_id=pessoa, regra=regra)
            )
            total += 1
            if not pessoa:
                continue
            ligadas += 1
            chave = f"{p['casa_parlamentar']}:{p['id_parlamentar']}"
            if chave not in vinculos:
                vinculos[chave] = session.scalar(
                    insert(PessoaVinculo)
                    .values(pessoa_id=pessoa, fonte=FONTE, id_externo=chave, regra=regra)
                    .returning(PessoaVinculo.id)
                )
            por_pessoa.setdefault(pessoa, ([], vinculos[chave]))[0].append(p["cargo"])
        for pessoa, (cargos, vinculo_id) in por_pessoa.items():
            linha = evento_da(c, cargos, pessoa, vinculo_id)
            session.execute(insert(Evento).values(**linha, fonte=FONTE, ingestao_id=ingestao_id))
            eventos += 1
    print(
        f"  {len(cpis)} CPIs/CPMIs; {total} participações, {ligadas} ligadas a uma pessoa; "
        f"{eventos} eventos"
    )
    return eventos


def normalizar(dados: dict) -> list[dict]:
    cd = dados["camara"]
    cpis = linhas_camara(cd["orgaos"], cd["membros"], cd["relatorios"])
    cpis += [c for c in map(linha_senado, dados["senado"]) if c]
    return cpis


# --- rede ---------------------------------------------------------------------------------------


def _html(client: httpx.Client, url: str) -> str:
    anterior = client.headers["Accept"]
    client.headers["Accept"] = "text/html"
    try:
        return comum.get_bytes(client, url).decode("utf-8", errors="replace")
    finally:
        client.headers["Accept"] = anterior


def _legislatura_atual() -> int:
    return PRIMEIRA_LEGISLATURA + (date.today().year - 2019) // 4


def baixar_camara(client: httpx.Client) -> dict:
    orgaos = orgaos_cpi_camara(comum.get_json(client, URL_CD_ORGAOS)["dados"])
    ids = {_id_final(o["uri"]) for o in orgaos}
    membros = []
    for leg in range(PRIMEIRA_LEGISLATURA, _legislatura_atual() + 1):
        try:
            dados = comum.get_json(client, URL_CD_MEMBROS.format(leg=leg))["dados"]
        except httpx.HTTPStatusError:
            continue  # legislatura ainda sem arquivo
        membros += [m for m in dados if _id_final(m["uriOrgao"]) in ids]
    return {"orgaos": orgaos, "membros": membros, "relatorios": relatorios_camara(client, orgaos)}


def relatorios_camara(client: httpx.Client, orgaos: list[dict]) -> dict[str, dict]:
    """Para cada CPI, o relatório achado nas tramitações dos requerimentos de criação (RCP)."""
    rcps = []
    pagina = 1
    while True:
        time.sleep(PAUSA)
        dados = comum.get_json(
            client,
            f"{API_CD}/proposicoes",
            params={
                "siglaTipo": "RCP",
                "dataApresentacaoInicio": DESDE,
                "itens": 100,
                "pagina": pagina,
            },
        )
        rcps += dados["dados"]
        if not any(link.get("rel") == "next" for link in dados.get("links", [])):
            break
        pagina += 1
    janelas = {}
    for o in orgaos:
        fim = _data(o.get("dataFim"))
        janelas[_id_final(o["uri"])] = (
            o.get("sigla"),
            _data(o.get("dataInicio")) or date.min,
            fim + timedelta(days=60) if fim else date.max,
        )
    relatorios: dict[str, dict] = {}
    for rcp in rcps:
        time.sleep(PAUSA)
        url = f"{API_CD}/proposicoes/{rcp['id']}/tramitacoes"
        tramitacoes = comum.get_json(client, url)["dados"]
        vistos = {t.get("siglaOrgao") for t in tramitacoes}
        for id_, (sigla, inicio, fim) in janelas.items():
            if sigla in vistos and id_ not in relatorios:
                achado = relatorio_camara(tramitacoes, sigla, inicio, fim)
                if achado:
                    relatorios[id_] = achado
    return relatorios


def baixar_senado(client: httpx.Client) -> list[dict]:
    codigos: dict[str, dict] = {}
    senadores: dict[str, None] = {}
    for leg in range(PRIMEIRA_LEGISLATURA, _legislatura_atual() + 1):
        time.sleep(PAUSA)
        dados = comum.get_json(client, f"{URL_SF}/senador/lista/legislatura/{leg}")
        for p in _lista(dados["ListaParlamentarLegislatura"]["Parlamentares"]["Parlamentar"]):
            senadores[str(p["IdentificacaoParlamentar"]["CodigoParlamentar"])] = None
    for codigo in senadores:
        time.sleep(PAUSA)
        dados = comum.get_json(client, f"{URL_SF}/senador/{codigo}/comissoes")
        comissoes = dados["MembroComissaoParlamentar"]["Parlamentar"].get("MembroComissoes") or {}
        codigos.update(comissoes_de_inquerito(_lista(comissoes.get("Comissao"))))
    # CPIs em atividade, inclusive as criadas que aguardam instalação (sem membros ainda).
    em_atividade = comum.get_json(client, f"{URL_SF}/comissao/lista/CPI")
    for c in colegiados_da_lista(em_atividade):
        codigo = str(c["CodigoColegiado"])
        codigos.setdefault(
            codigo,
            {
                "codigo": codigo,
                "sigla": c.get("SiglaColegiado") or "",
                "nome": c.get("NomeColegiado") or "",
                "casa": c.get("SiglaCasa") or "SF",
            },
        )["data_inicio"] = c.get("DataInicio")
    colegiados = []
    for col in codigos.values():
        time.sleep(PAUSA)
        col["comissao_html"] = _html(client, URL_SF_COMISSAO.format(codigo=col["codigo"]))
        time.sleep(PAUSA)
        col["composicao_html"] = _html(client, URL_SF_COMPOSICAO.format(codigo=col["codigo"]))
        colegiados.append(col)
    return colegiados


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> dict:
        return {"camara": baixar_camara(client), "senado": baixar_senado(client)}

    def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
        return gravar(session, normalizar(payload), ingestao.id)

    return comum.executar_ingestao(
        FONTE, URL_CD_ORGAOS, baixar, carregar, de_raw=de_raw,
        incremental=comum.Incremental(chave=FONTE, contexto=comum.contexto_pessoas),
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    print(f"{FONTE}: {executar(parser.parse_args().de_raw)} participações na linha do tempo")
