"""Cassações e outros julgamentos de candidatura registrados pelo TSE (motivo_cassacao), só
das pessoas que já temos (eleitos e parlamentares), gravados como eventos da linha do
tempo.

O arquivo traz, por candidatura, o número do processo e os fundamentos, de dois tipos:
- "Fundamentos legais de cassação": cassação do registro ou do diploma (abuso de poder,
  compra de voto, fraude à cota de gênero...);
- "Fundamentos legais de julgamento": julgamento sobre o registro da candidatura (ausência
  de condição de elegibilidade, inelegibilidade, partido ou coligação indeferidos...). Em
  2022 todas as linhas vêm com este tipo, inclusive "Abuso de poder político", que é
  fundamento de cassação: por isso o texto repete a linguagem do TSE ("julgamento") e não
  afirma que houve indeferimento.

Não traz a data da decisão nem se ainda cabe recurso: o evento diz o que o TSE registra,
com a data em que o arquivo foi gerado. Rode depois de ingestion.pessoas.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, PessoaVinculo
from ingestion import comum
from ingestion.normalizar import numero_cnj
from ingestion.tse import comum_tse

FONTE = "tse_cassacoes"
URL = f"{comum_tse.BASE}/motivo_cassacao/motivo_cassacao_{{ano}}.zip"
URL_DADOS = "https://dadosabertos.tse.jus.br/dataset/candidatos-{ano}"
TIPOS = {
    "fundamentos legais de cassação": "cassacao",
    "fundamentos legais de julgamento": "julgamento_candidatura",
}


def normalizar(linhas: Any) -> list[dict[str, Any]]:
    """Uma entrada por candidatura, processo e tipo, com os fundamentos juntos (o arquivo
    tem uma linha por fundamento)."""
    grupos: dict[tuple, dict[str, Any]] = {}
    for linha in linhas:
        if "DS_TP_MOTIVO" in linha:
            tipo = TIPOS.get((linha.get("DS_TP_MOTIVO") or "").strip().lower())
        else:
            # Arquivos antigos (2016) não têm o tipo nem o processo: só o motivo. Sem saber
            # se foi cassação, fica a forma neutra ("julgamento sobre o registro").
            tipo = "julgamento_candidatura"
        if tipo is None:
            continue
        numero = numero_cnj(linha.get("NR_PROCESSO"))
        chave = (linha["ANO_ELEICAO"].strip(), linha["SQ_CANDIDATO"].strip(), numero, tipo)
        grupo = grupos.setdefault(
            chave,
            {
                "ano": int(chave[0]),
                "sq_candidato": chave[1],
                "numero_processo": numero,
                "tipo": tipo,
                "fundamentos": [],
                "gerado_em": comum_tse.data(linha.get("DT_GERACAO")),
            },
        )
        fundamento = comum_tse.texto(linha.get("DS_MOTIVO") or linha.get("DS_MOTIVO_CASSACAO"))
        if fundamento and fundamento not in grupo["fundamentos"]:
            grupo["fundamentos"].append(fundamento.rstrip("."))
    return list(grupos.values())


def descricao(registro: dict[str, Any]) -> str:
    fundamentos = "; ".join(registro["fundamentos"]) or "não informado"
    if registro["tipo"] == "cassacao":
        return (
            f"O TSE registra a cassação do registro ou do diploma da candidatura de "
            f"{registro['ano']}. Fundamento: {fundamentos}."
        )
    return (
        f"O TSE registra julgamento sobre o registro da candidatura de {registro['ano']}, "
        f"com fundamento em: {fundamentos}."
    )


def eventos(
    registros: list[dict[str, Any]], vinculos: dict[str, tuple[int, int]], ingestao_id: int
) -> list[dict[str, Any]]:
    """Só as candidaturas ligadas a uma pessoa (id_externo "ano:sq" -> (vínculo, pessoa))."""
    linhas = []
    for r in registros:
        ligacao = vinculos.get(f"{r['ano']}:{r['sq_candidato']}")
        if ligacao is None:
            continue
        gerado: date | None = r["gerado_em"]
        linhas.append(
            {
                "pessoa_id": ligacao[1],
                "vinculo_id": ligacao[0],
                "data": None,  # o arquivo não traz a data da decisão
                "tipo": r["tipo"],
                "descricao": descricao(r),
                "orgao": "Justiça Eleitoral",
                "numero_processo": r["numero_processo"],
                "situacao": f"segundo o TSE em {gerado:%d/%m/%Y}" if gerado else None,
                "fonte": FONTE,
                "id_externo": f"{r['ano']}:{r['sq_candidato']}:{r['numero_processo'] or ''}",
                "fonte_url": URL_DADOS.format(ano=r["ano"]),
                "ingestao_id": ingestao_id,
            }
        )
    return linhas


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        lidas = comum.ContaLinhas(comum_tse.linhas(payload, "motivo_cassacao_"))
        registros = normalizar(lidas)
        if not registros:
            raise RuntimeError(f"Arquivo de cassações de {ano} vazio: nada alterado.")
        comum.conferir_carga(
            ingestao,
            registros,
            total_fonte=lidas.total,
            nao_nulos=("sq_candidato",),
            unica=("ano", "sq_candidato", "numero_processo", "tipo"),
        )
        vinculos = {
            id_externo: (vinculo, pessoa)
            for id_externo, vinculo, pessoa in session.execute(
                select(PessoaVinculo.id_externo, PessoaVinculo.id, PessoaVinculo.pessoa_id).where(
                    PessoaVinculo.fonte == "candidatura",
                    PessoaVinculo.id_externo.like(f"{ano}:%"),
                )
            )
        }
        linhas = eventos(registros, vinculos, ingestao.id)
        session.execute(
            delete(Evento).where(Evento.fonte == FONTE, Evento.id_externo.like(f"{ano}:%"))
        )
        if linhas:
            session.execute(insert(Evento), linhas)
        print(f"  {ano}: {len(registros)} no arquivo, {len(linhas)} de pessoas que temos")
        return len(linhas)

    return comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(
            sonda=URL.format(ano=ano), contexto=comum.contexto_candidaturas(ano)
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2016, 2018, 2020, 2022, 2024])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} eventos")
