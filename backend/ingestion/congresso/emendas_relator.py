"""Emendas de relator-geral (RP9, o "orçamento secreto"): indicações com o parlamentar que pediu.

Fonte: planilha consolidada que a Comissão Mista de Orçamento publica na página "Indicações
para execução orçamentária em RP9 - LOA 2022" (xlsx, ~3 MB, 16,6 mil indicações de
beneficiários registradas em 2022). É o único registro oficial aberto que traz o autor do
pedido: nas emendas do Portal da Transparência o autor é sempre "RELATOR GERAL". Para a LOA
2020 e 2021 a CMO publicou só a relação de beneficiários (sem autor) e PDFs de ofícios em
texto livre, que não ligam cada pedido a uma linha da relação; ficam de fora.

O autor vem com o nome civil e o tipo (Deputado, Senador, Usuário Externo). Só deputados e
senadores entram, ligados ao parlamentar da base pelo nome (civil ou parlamentar) comparado
sem acentos, na mesma Casa, só com correspondência exata e única. Quem não está na base
(muitos deputados da legislatura passada) fica de fora. O valor é o solicitado: a planilha
não traz empenho nem pagamento.

O xlsx é lido com a biblioteca padrão (zip + xml), sem dependência nova.
"""

import argparse
import io
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import EmendaRelatorIndicacao, FonteIngestao, Parlamentar
from ingestion import comum

FONTE = "congresso_emendas_relator"
URL_PAGINA = (
    "https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/"
    "Indicacoes-para-execucao-orcamentaria-em-RP9_LOA-2022"
)
URL = (
    "https://www.camara.leg.br/internet/comissao/index/mista/orca/orcamento/"
    "EXECUCAO-RP9/LOA-2022/Relacao-de-indicacoes-Consolidado.xlsx"
)
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CASAS = {"Deputado": "camara", "Senador": "senado"}
COLUNAS = {
    "numero": "Número",
    "ano": "Ano",
    "data": "Data de cadastro",
    "autor": "Autor",
    "tipo_autor": "Tipo autor",
    "beneficiario": "Nome beneficiário",
    "uf": "Uf beneficiário",
    "orgao": "Nome órgão",
    "unidade": "Nome uo",
    "acao": "Cod ação",
    "objeto": "Objeto",
    "valor": "Valor Solicitado",
}


def _texto(valor: str | None, limite: int) -> str | None:
    valor = " ".join((valor or "").split())
    return valor[:limite] or None


def ler_planilha(conteudo: bytes) -> list[dict[str, str | None]]:
    """Primeira aba do xlsx como lista de dicts (cabeçalho = primeira linha)."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        compartilhadas = [
            "".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
            for si in ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
        ]
        linhas = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(
            f"{{{NS['m']}}}row"
        )
        tabela: list[list[str | None]] = []
        for linha in linhas:
            valores: list[str | None] = []
            for c in linha.findall("m:c", NS):
                # Células vazias podem faltar na linha: a posição vem da referência (A1, C1).
                coluna = 0
                for letra in "".join(ch for ch in c.get("r", "") if ch.isalpha()):
                    coluna = coluna * 26 + ord(letra) - 64
                v = c.find("m:v", NS)
                valor = None
                if v is not None:
                    valor = compartilhadas[int(v.text)] if c.get("t") == "s" else v.text
                valores.extend([None] * (coluna - 1 - len(valores)))
                valores.append(valor)
            tabela.append(valores)
    if not tabela:
        return []
    cabecalho = tabela[0]
    return [
        {nome: (linha[i] if i < len(linha) else None) for i, nome in enumerate(cabecalho) if nome}
        for linha in tabela[1:]
    ]


def normalizar(conteudo: bytes) -> list[dict[str, Any]]:
    """Indicações de deputados e senadores. Usuário externo (prefeito, entidade, particular)
    não é parlamentar e fica de fora."""
    registros = []
    vistos: set[int] = set()
    for linha in ler_planilha(conteudo):
        tipo = (linha.get(COLUNAS["tipo_autor"]) or "").strip()
        numero = linha.get(COLUNAS["numero"])
        if tipo not in CASAS or not numero or int(numero) in vistos:
            continue
        vistos.add(int(numero))
        # O cabeçalho oficial tem erro de digitação ("Cnpj beneficário"): acha pelo prefixo.
        bruto = next((v for k, v in linha.items() if k.lower().startswith("cnpj")), None)
        cnpj = "".join(ch for ch in (bruto or "") if ch.isdigit())
        data = linha.get(COLUNAS["data"])
        registros.append(
            {
                "numero": int(numero),
                "ano": int(linha[COLUNAS["ano"]] or 0),
                "data_cadastro": (date(1899, 12, 30) + timedelta(days=int(float(data))))
                if data
                else None,
                "casa": CASAS[tipo],
                "autor_nome": _texto(linha.get(COLUNAS["autor"]), 200) or "",
                "beneficiario": _texto(linha.get(COLUNAS["beneficiario"]), 300) or "",
                # CNPJ de 14 dígitos; qualquer outra coisa não é identificador de empresa.
                "beneficiario_cnpj": cnpj if len(cnpj) == 14 else None,
                "uf": _texto(linha.get(COLUNAS["uf"]), 2),
                "orgao": _texto(linha.get(COLUNAS["orgao"]), 150),
                "unidade": _texto(linha.get(COLUNAS["unidade"]), 200),
                "acao": _texto(linha.get(COLUNAS["acao"]), 20),
                "objeto": _texto(linha.get(COLUNAS["objeto"]), 500),
                "valor_solicitado": Decimal(linha.get(COLUNAS["valor"]) or "0"),
            }
        )
    return registros


def vincular(
    registros: list[dict[str, Any]], parlamentares: list[tuple[int, str, str, str | None]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Liga o autor ao parlamentar (id, casa, nome parlamentar, nome civil). Devolve as
    indicações ligadas e a contagem das que ficaram de fora, por motivo."""
    por_nome: dict[tuple[str, str], set[int]] = defaultdict(set)
    for id_, casa, nome, civil in parlamentares:
        for n in (nome, civil):
            if n:
                por_nome[(casa, comum.chave_nome(n))].add(id_)
    ligadas, fora = [], {"fora_da_base": 0, "ambiguo": 0}
    for r in registros:
        candidatos = por_nome.get((r["casa"], comum.chave_nome(r["autor_nome"])), set())
        if len(candidatos) == 1:
            ligadas.append({**r, "parlamentar_id": next(iter(candidatos))})
        else:
            fora["ambiguo" if candidatos else "fora_da_base"] += 1
    return ligadas, fora


def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    registros = normalizar(conteudo)
    if not registros:
        raise ValueError("Nenhuma indicação de parlamentar na planilha; abortando.")
    parlamentares = session.execute(
        select(
            Parlamentar.id, Parlamentar.casa, Parlamentar.nome_parlamentar, Parlamentar.nome_civil
        )
    ).all()
    ligadas, fora = vincular(registros, [tuple(p) for p in parlamentares])
    print(
        f"  indicações de deputados e senadores: {len(registros)}; ligadas: {len(ligadas)}; "
        f"autor fora da base: {fora['fora_da_base']}; nome ambíguo: {fora['ambiguo']}"
    )
    if not ligadas:
        raise ValueError("Nenhuma indicação ligada a parlamentar da base; abortando.")
    session.execute(delete(EmendaRelatorIndicacao))
    linhas = [
        {**{k: v for k, v in r.items() if k != "casa"}, "ingestao_id": ingestao.id} for r in ligadas
    ]
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(EmendaRelatorIndicacao), linhas[inicio : inicio + 5000])
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        client.headers["Accept"] = "*/*"  # o servidor da Câmara responde 406 a application/json
        return comum.get_bytes(client, URL)

    return comum.executar_ingestao(
        FONTE, URL, baixar, carregar, de_raw=de_raw, extensao_raw=".xlsx", incremental=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} indicações")
