"""Assembleia Legislativa de São Paulo (ALESP): deputados no cargo hoje, projetos,
proposições e gastos do gabinete, pelos arquivos de dados abertos (XML, atualizados todo
dia em `repositorioDados`).

Grava nas mesmas tabelas das outras casas, pela gravação do conector SAPL, inclusive o voto
de cada deputado nas comissões permanentes (`comissoes_permanentes_votacoes.xml`). O que os
dados abertos não trazem: o voto de cada deputado no Plenário e a presença em Plenário (o
site mostra a presença num formulário e recusa acesso automatizado à página de votações; não
contornamos).

Arquivos e armadilhas (ver docs/FONTES_DE_DADOS.md):
- `deputados.xml`: só quem está em exercício (94). `IdSPL` é o id usado na autoria;
  `Matricula` é o usado nos gastos;
- `proposituras.zip` (130 MB descompactado) e `documento_autor.zip` (145 MB): lidos em
  fluxo; a natureza da propositura é um código (`naturezasSpl.xml`);
- `despesas_gabinetes.xml` (164 MB, desde 2015, sem compactação): lido em fluxo e somado
  por deputado, mês e categoria ("A - COMBUSTÍVEIS E LUBRIFICANTES" vira "Combustíveis e
  lubrificantes");
- `comissoes_permanentes_votacoes.xml` (65 MB, desde 2005, sem compactação): um voto por
  linha, sem data; a data vem da reunião (`comissoes_permanentes_reunioes.xml`) e o nome da
  comissão de `comissoes.xml`. O campo `IdDeputado` desse arquivo traz o `IdSPL`. Uma
  votação é uma matéria (`IdDocumento`) numa reunião (`IdReuniao`).
"""

import argparse
import io
import re
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import IO, Any
from xml.etree import ElementTree

from sqlalchemy import bindparam, update
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, VotacaoLocal
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alesp"
REPOSITORIO = "https://www.al.sp.gov.br/repositorioDados/"
SITE = "https://www.al.sp.gov.br/"
# Naturezas (naturezasSpl.xml): projetos guardados com ementa; as demais, só contagem.
PROJETOS = {
    "1": "Projeto de Lei",
    "2": "Projeto de Lei Complementar",
    "3": "Projeto de Resolução",
    "4": "Projeto de Decreto Legislativo",
    "5": "Proposta de Emenda à Constituição",
}
CONTAGEM = {"6": "Moção", "7": "Requerimento", "8": "Requerimento de Informação", "9": "Indicação"}
LETRA_DA_CATEGORIA = re.compile(r"^[A-Z]\s*-\s*")


def registros(arquivo: IO[bytes], tag: str) -> Any:
    """Cada <tag> do XML como dicionário {campo: texto}, sem carregar o arquivo inteiro."""
    for _, elemento in ElementTree.iterparse(arquivo, events=("end",)):
        if elemento.tag == tag:
            yield {filho.tag: (filho.text or "").strip() for filho in elemento}
            elemento.clear()


def _abrir(caminho: Path | bytes) -> IO[bytes]:
    """Um .zip com um XML dentro, ou o próprio XML."""
    bruto = io.BytesIO(caminho) if isinstance(caminho, bytes) else caminho.open("rb")
    if zipfile.is_zipfile(bruto):
        bruto.seek(0)
        z = zipfile.ZipFile(bruto)
        return z.open(z.namelist()[0])
    bruto.seek(0)
    return bruto


def _baixar_e_ler(client: Any, caminho: str, ler: Any, *args: Any) -> Any:
    """Baixa para o disco, lê em fluxo e apaga (fechando antes: no Windows, apagar um
    arquivo aberto falha)."""
    arquivo = comum.baixar_para_arquivo(client, REPOSITORIO + caminho)
    try:
        with arquivo.open("rb") as bruto:
            if zipfile.is_zipfile(bruto):
                bruto.seek(0)
                with zipfile.ZipFile(bruto) as z, z.open(z.namelist()[0]) as xml:
                    return ler(xml, *args)
            bruto.seek(0)
            return ler(bruto, *args)
    finally:
        arquivo.unlink(missing_ok=True)


def deputados(arquivo: IO[bytes]) -> list[dict]:
    return [d for d in registros(arquivo, "Deputado") if d.get("Situacao") == "EXE"]


def proposituras(
    arquivo: IO[bytes], anos: set[int], citadas: set[str] | None = None
) -> tuple[dict[str, dict], dict[str, dict]]:
    """IdDocumento -> propositura, só as do período e das naturezas que interessam (para a
    autoria); e, à parte, as `citadas` (votadas nas comissões), de qualquer ano e natureza."""
    resultado = {}
    outras = {}
    for p in registros(arquivo, "propositura"):
        if citadas and p.get("IdDocumento") in citadas:
            outras[p["IdDocumento"]] = p
        natureza = p.get("IdNatureza", "")
        if natureza not in PROJETOS and natureza not in CONTAGEM:
            continue
        if not p.get("AnoLegislativo", "").isdigit() or int(p["AnoLegislativo"]) not in anos:
            continue
        resultado[p["IdDocumento"]] = p
    return resultado, outras


def autorias(arquivo: IO[bytes], documentos: set[str]) -> dict[str, list[str]]:
    """IdDocumento -> autores (IdSPL), na ordem do arquivo (o primeiro é o principal)."""
    resultado: dict[str, list[str]] = defaultdict(list)
    for a in registros(arquivo, "DocumentoAutor"):
        if a.get("IdDocumento") in documentos:
            resultado[a["IdDocumento"]].append(a.get("IdAutor", ""))
    return resultado


def distribuir(props: dict[str, dict], autores: dict[str, list[str]], ids: set[str]) -> dict:
    por_deputado: dict[str, dict] = {i: {"contagem": {}, "projetos": []} for i in ids}
    for documento, p in props.items():
        natureza = p["IdNatureza"]
        tipo = PROJETOS.get(natureza) or CONTAGEM[natureza]
        for ordem, autor in enumerate(autores.get(documento, [])):
            if autor not in por_deputado:
                continue
            dep = por_deputado[autor]
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if natureza in PROJETOS:
                numero = p.get("NroLegislativo")
                dep["projetos"].append(
                    {
                        "id_externo": documento,
                        "tipo": tipo,
                        "numero": int(numero) if numero and numero.isdigit() else None,
                        "ano": int(p["AnoLegislativo"]),
                        "ementa": " ".join(p.get("Ementa", "").split()),
                        "data_apresentacao": (p.get("DtPublicacao") or "")[:10] or None,
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": f"{SITE}propositura/?id={documento}",
                    }
                )
    return por_deputado


def categoria(tipo: str) -> str:
    return comum.limpar_categoria(LETRA_DA_CATEGORIA.sub("", tipo or ""))[:200]


def gastos(arquivo: IO[bytes], anos: set[int], matriculas: set[str]) -> dict[str, list[dict]]:
    """Matrícula -> gastos somados por ano, mês e categoria."""
    soma: dict[tuple, Decimal] = defaultdict(Decimal)
    for d in registros(arquivo, "despesa"):
        if d.get("Matricula") not in matriculas or not d.get("Ano", "").isdigit():
            continue
        if int(d["Ano"]) not in anos:
            continue
        try:
            valor = Decimal(d.get("Valor") or "0")
        except InvalidOperation:
            continue
        soma[(d["Matricula"], int(d["Ano"]), int(d["Mes"]), categoria(d.get("Tipo", "")))] += valor
    resultado: dict[str, list[dict]] = defaultdict(list)
    for (matricula, ano, mes, cat), valor in soma.items():
        resultado[matricula].append({"ano": ano, "mes": mes, "categoria": cat, "valor": valor})
    return resultado


# Comissões: o voto vem em texto livre ("Favorável ao voto do relator", "Favorável à moção,
# conclusivamente"...) e numa letra (`TipoVoto`). O texto é guardado como veio quando cabe
# na coluna (30 caracteres); senão, vale o rótulo da letra.
TIPO_VOTO = {
    "F": "Favorável ao parecer",
    "P": "Favorável à proposição",
    "C": "Contrário ao parecer",
    "T": "Contrário à proposição",
    "S": "Voto em separado",
    "A": "Abstenção",
    "B": "Em branco",
}
FAVORAVEL = {"F", "P"}
CONTRARIO = {"C", "T"}


def reunioes(arquivo: IO[bytes], anos: set[int]) -> dict[str, dict]:
    """IdReuniao -> data e comissão, só as reuniões do período."""
    resultado = {}
    for r in registros(arquivo, "ReuniaoComissao"):
        data = (r.get("Data") or "")[:10]
        if data[:4].isdigit() and int(data[:4]) in anos:
            resultado[r["IdReuniao"]] = {"data": data, "comissao": r.get("IdComissao", "")}
    return resultado


def comissoes(arquivo: IO[bytes]) -> dict[str, str]:
    return {c["IdComissao"]: c.get("NomeComissao", "") for c in registros(arquivo, "Comissao")}


def votos_em_comissao(arquivo: IO[bytes], periodo: dict[str, dict]) -> list[dict]:
    """Os votos dados nas reuniões do período (de todos os deputados, para os totais)."""
    return [
        v
        for v in registros(arquivo, "ReuniaoComissaoVotacao")
        if v.get("IdReuniao") in periodo and v.get("IdDocumento")
    ]


def texto_do_voto(voto: dict) -> str:
    texto = " ".join((voto.get("Voto") or "").split()).rstrip(".")
    if texto.lower() == "não registrou voto":
        return "Não votou"
    if texto and len(texto) <= 30:
        return texto
    return TIPO_VOTO.get(voto.get("TipoVoto", ""), texto[:30] or "Não informado")


def descrever(documento: str, propositura: dict | None) -> str:
    if not propositura:
        return f"documento {documento}"
    natureza = propositura.get("IdNatureza", "")
    tipo = PROJETOS.get(natureza) or CONTAGEM.get(natureza) or "Proposição"
    numero, ano = propositura.get("NroLegislativo"), propositura.get("AnoLegislativo")
    return f"{tipo} nº {numero} de {ano}" if numero and ano else tipo


def _id_externo(reuniao: str, documento: str) -> str:
    """Reunião e documento em hexadecimal: os dois ids juntos, em decimal, passam dos 20
    caracteres da coluna."""
    return f"{int(reuniao):x}-{int(documento):x}"


def votacoes_em_comissao(
    votos: list[dict],
    periodo: dict[str, dict],
    nomes: dict[str, str],
    documentos: dict[str, dict],
    ids: set[str],
) -> dict:
    """Uma votação por matéria e reunião, com os totais de todos os votantes e o voto de
    quem está em exercício hoje. Votação sem nenhum deputado em exercício não entra."""
    por_votacao: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for v in votos:
        por_votacao[(v["IdReuniao"], v["IdDocumento"])].append(v)
    votacoes, registrados = [], []
    for (reuniao, documento), lista in por_votacao.items():
        id_externo = _id_externo(reuniao, documento)
        deste = [
            {"votacao": id_externo, "parlamentar": v["IdDeputado"], "voto": texto_do_voto(v)}
            for v in lista
            if v.get("IdDeputado") in ids
        ]
        if not deste:
            continue
        registrados.extend(deste)
        comissao = periodo[reuniao]["comissao"]
        nome = nomes.get(comissao) or f"Comissão {comissao}"
        # "Não registrou voto" vem com a letra F: não conta como favorável.
        tipos = [v.get("TipoVoto", "") for v in lista if texto_do_voto(v) != "Não votou"]
        votacoes.append(
            {
                "id_externo": id_externo,
                "materia": f"{nome}: {descrever(documento, documentos.get(documento))}",
                "resultado": None,  # os dados abertos não trazem o resultado da votação
                "sim": sum(t in FAVORAVEL for t in tipos),
                "nao": sum(t in CONTRARIO for t in tipos),
                "abstencoes": sum(t == "A" for t in tipos),
                "data": periodo[reuniao]["data"],
                "url": f"{SITE}propositura/?id={documento}",
            }
        )
    return {"votacoes": votacoes, "votos": registrados}


def coletar(hoje: date) -> dict:
    anos = {hoje.year, hoje.year - 1}
    with comum.criar_cliente() as client:
        lista = deputados(_abrir(comum.get_bytes(client, REPOSITORIO + "deputados/deputados.xml")))
        ids = {d["IdSPL"] for d in lista}
        periodo = reunioes(
            _abrir(
                comum.get_bytes(
                    client, REPOSITORIO + "processo_legislativo/comissoes_permanentes_reunioes.xml"
                )
            ),
            anos,
        )
        nomes = comissoes(
            _abrir(comum.get_bytes(client, REPOSITORIO + "processo_legislativo/comissoes.xml"))
        )
        votos = _baixar_e_ler(
            client,
            "processo_legislativo/comissoes_permanentes_votacoes.xml",
            votos_em_comissao,
            periodo,
        )
        props, votadas = _baixar_e_ler(
            client,
            "processo_legislativo/proposituras.zip",
            proposituras,
            anos,
            {v["IdDocumento"] for v in votos},
        )
        autores = _baixar_e_ler(
            client, "processo_legislativo/documento_autor.zip", autorias, set(props)
        )
        por_matricula = _baixar_e_ler(
            client,
            "deputados/despesas_gabinetes.xml",
            gastos,
            anos,
            {d.get("Matricula", "") for d in lista},
        )
    autoria = distribuir(props, autores, ids)
    em_comissao = votacoes_em_comissao(votos, periodo, nomes, votadas, ids)
    vereadores = [
        {
            "id_externo": d["IdSPL"],
            "nome": d.get("NomeParlamentar", "").strip(),
            "nome_completo": None,
            "partido": d.get("Partido") or None,
            "foto_url": None,  # a foto vem do TSE, pela ligação ao eleito
            "email": d.get("Email") or None,
            "telefone": d.get("Telefone") or None,
            "titular": True,  # o arquivo não diz se é suplente
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[d["IdSPL"]]["contagem"],
            "projetos": autoria[d["IdSPL"]]["projetos"],
            "sessoes": None,
            "presencas": None,
            "gastos": por_matricula.get(d.get("Matricula", ""), []),
        }
        for d in lista
    ]
    return {
        "base": SITE,
        "legislatura": None,
        "vereadores": vereadores,
        **em_comissao,
    }


def gravar(session: Session, casa: dict) -> int:
    """Grava pela gravação do SAPL e depois põe o link de cada votação na página da
    propositura (o SAPL monta o link a partir do id da matéria, que aqui não existe)."""
    links = {v["id_externo"]: v["url"] for v in casa["votacoes"]}
    votacoes = [{k: val for k, val in v.items() if k != "url"} for v in casa["votacoes"]]
    total = sapl.gravar(session, None, {**casa, "votacoes": votacoes}, uf="SP")
    tabela = VotacaoLocal.__table__
    if links:
        session.execute(
            update(tabela)
            .where(
                tabela.c.casa == "assembleia",
                tabela.c.uf == "SP",
                tabela.c.id_externo == bindparam("externo"),
            )
            .values(url=bindparam("link")),
            [{"externo": e, "link": u} for e, u in links.items()],
        )
    return total


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 60:  # a ALESP tem 94 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALESP; abortando.")
    if not casa["votacoes"]:  # são centenas de reuniões por ano: lista vazia é falha da fonte
        raise ValueError("Nenhuma votação de comissão da ALESP no período; abortando.")
    with SessionLocal() as session:
        total = gravar(session, casa)
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url=REPOSITORIO,
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(
        f"ALESP: {total} deputados, {len(casa['votacoes'])} votações e "
        f"{len(casa['votos'])} votos em comissões",
        flush=True,
    )
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
