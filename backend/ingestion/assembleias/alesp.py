"""Assembleia Legislativa de São Paulo (ALESP): deputados no cargo hoje, projetos,
proposições e gastos do gabinete, pelos arquivos de dados abertos (XML, atualizados todo
dia em `repositorioDados`).

Grava nas mesmas tabelas das outras casas, pela gravação do conector SAPL. O que os dados
abertos não trazem: o voto de cada deputado no Plenário e a presença em Plenário (o site
mostra a presença num formulário e recusa acesso automatizado à página de votações; não
contornamos).

Arquivos e armadilhas (ver docs/FONTES_DE_DADOS.md):
- `deputados.xml`: só quem está em exercício (94). `IdSPL` é o id usado na autoria;
  `Matricula` é o usado nos gastos;
- `proposituras.zip` (130 MB descompactado) e `documento_autor.zip` (145 MB): lidos em
  fluxo; a natureza da propositura é um código (`naturezasSpl.xml`);
- `despesas_gabinetes.xml` (164 MB, desde 2015, sem compactação): lido em fluxo e somado
  por deputado, mês e categoria ("A - COMBUSTÍVEIS E LUBRIFICANTES" vira "Combustíveis e
  lubrificantes").
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

from app.db import SessionLocal
from app.models import FonteIngestao
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


def proposituras(arquivo: IO[bytes], anos: set[int]) -> dict[str, dict]:
    """IdDocumento -> propositura, só as do período e das naturezas que interessam."""
    resultado = {}
    for p in registros(arquivo, "propositura"):
        natureza = p.get("IdNatureza", "")
        if natureza not in PROJETOS and natureza not in CONTAGEM:
            continue
        if not p.get("AnoLegislativo", "").isdigit() or int(p["AnoLegislativo"]) not in anos:
            continue
        resultado[p["IdDocumento"]] = p
    return resultado


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


def coletar(hoje: date) -> dict:
    anos = {hoje.year, hoje.year - 1}
    with comum.criar_cliente() as client:
        lista = deputados(_abrir(comum.get_bytes(client, REPOSITORIO + "deputados/deputados.xml")))
        ids = {d["IdSPL"] for d in lista}
        props = _baixar_e_ler(client, "processo_legislativo/proposituras.zip", proposituras, anos)
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
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 60:  # a ALESP tem 94 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALESP; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="SP")
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
    print(f"ALESP: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
