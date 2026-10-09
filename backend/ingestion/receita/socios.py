"""Sócios das empresas que aparecem nos nossos dados (empresas sancionadas pela CGU e os
maiores fornecedores de prefeituras e câmaras), só os que são pessoas que acompanhamos.

Fonte: o quadro de sócios da Receita Federal, consultado por CNPJ na API do Querido
Diário (Open Knowledge Brasil), que republica os dados abertos do CNPJ. É um espelho
confiável de dado oficial (degrau "espelho" da escada de acesso): o endereço do arquivo
da própria Receita mudou e não está acessível. Conferir por amostra contra a Receita
quando o arquivo voltar.

Educação com um serviço comunitário: uma consulta a cada 2 segundos, novas tentativas em
503 e cache de 30 dias por CNPJ (cnpj_consulta). O sócio pessoa física vem com o CPF
mascarado (***606618**) e o nome: a ligação é forte (6 dígitos do meio + nome igual) e
só com pessoas que têm CPF.
"""

import argparse
import re
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    CnpjConsulta,
    DespesaFornecedor,
    FonteIngestao,
    Pessoa,
    SancaoEmpresa,
    SocioPessoa,
)
from ingestion import comum

FONTE = "cnpj_socios"
URL = "https://api.queridodiario.org.br/company/partners/{cnpj}"
PAUSA = 2.0
VALIDADE = timedelta(days=30)
MAIORES_FORNECEDORES = 1000


def cnpjs_de_interesse(session: Session) -> list[str]:
    """Empresas sancionadas que aparecem como fornecedores e os maiores fornecedores
    (soma paga em todos os anos guardados)."""
    sancionadas = set(session.scalars(select(SancaoEmpresa.cnpj).distinct()))
    maiores = session.scalars(
        select(DespesaFornecedor.documento)
        .where(DespesaFornecedor.documento.is_not(None))
        .group_by(DespesaFornecedor.documento)
        .order_by(func.sum(DespesaFornecedor.valor_pago).desc())
        .limit(MAIORES_FORNECEDORES)
    )
    return sorted(sancionadas | set(maiores))


def socios_pessoa_fisica(resposta: dict) -> list[dict[str, Any]]:
    """Sócios pessoa física com CPF mascarado: (meio do CPF, nome, qualificação, entrada)."""
    resultado = []
    for p in resposta.get("partners") or []:
        if not (p.get("identificador_socio") or "").startswith("2"):
            continue
        meio = re.sub(r"\D", "", p.get("cnpj_cpf_socio") or "")
        if len(meio) != 6:
            continue
        entrada = None
        try:
            entrada = datetime.strptime(p.get("data_entrada_sociedade") or "", "%d/%m/%Y").date()
        except ValueError:
            pass
        qualificacao = re.sub(r"^\d+\s*-\s*", "", p.get("qualificacao_socio") or "").strip()
        resultado.append(
            {
                "meio": meio,
                "nome": (p.get("razao_social") or "").strip(),
                "qualificacao": qualificacao[:80] or None,
                "entrada": entrada,
            }
        )
    return resultado


def ligar(socios: list[dict], por_meio_nome: dict[tuple[str, str], set[int]]) -> list[tuple]:
    """(pessoa, sócio) só quando os 6 dígitos + nome apontam para uma única pessoa."""
    ligados = []
    for s in socios:
        pessoas = por_meio_nome.get((s["meio"], comum.chave_nome(s["nome"])), set())
        if len(pessoas) == 1:
            ligados.append((next(iter(pessoas)), s))
    return ligados


def consultar(client: httpx.Client, cnpj: str) -> dict | None:
    for tentativa in range(1, 5):
        time.sleep(PAUSA)
        try:
            resposta = client.get(URL.format(cnpj=cnpj))
        except httpx.TransportError:
            time.sleep(10 * tentativa)
            continue
        if resposta.status_code == 404:
            return {"partners": []}
        if resposta.status_code == 200:
            try:
                return resposta.json()
            except ValueError:
                return None
        time.sleep(10 * tentativa)  # 503 "no available server": espera e tenta de novo
    return None


def executar() -> int:
    hoje = date.today()
    with SessionLocal() as session:
        ingestao = FonteIngestao(
            fonte=FONTE, url=URL.format(cnpj="{cnpj}"), arquivo_raw="(não guardado)"
        )
        session.add(ingestao)
        session.flush()
        recentes = set(
            session.scalars(
                select(CnpjConsulta.cnpj).where(CnpjConsulta.consultado_em >= hoje - VALIDADE)
            )
        )
        pendentes = [c for c in cnpjs_de_interesse(session) if c not in recentes]
        por_meio_nome: dict[tuple[str, str], set[int]] = {}
        for id_, cpf, chave in session.execute(
            select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome).where(Pessoa.cpf.is_not(None))
        ):
            por_meio_nome.setdefault((cpf[3:9], chave), set()).add(id_)
        session.commit()
        print(f"  {len(pendentes)} CNPJs a consultar ({len(recentes)} no cache)", flush=True)
        ligados_total, falhas = 0, 0
        with comum.criar_cliente() as client:
            for i, cnpj in enumerate(pendentes, start=1):
                resposta = consultar(client, cnpj)
                if resposta is None:
                    falhas += 1
                    continue
                socios = socios_pessoa_fisica(resposta)
                ligados = ligar(socios, por_meio_nome)
                session.execute(delete(SocioPessoa).where(SocioPessoa.cnpj == cnpj))
                for pessoa, s in ligados:
                    session.execute(
                        insert(SocioPessoa)
                        .values(pessoa_id=pessoa, cnpj=cnpj, qualificacao=s["qualificacao"],
                                data_entrada=s["entrada"])
                        .on_conflict_do_nothing()
                    )  # fmt: skip
                total_socios = len(resposta.get("partners") or [])
                stmt = insert(CnpjConsulta).values(
                    cnpj=cnpj, consultado_em=hoje, socios=total_socios
                )
                session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=["cnpj"],
                        set_={"consultado_em": stmt.excluded.consultado_em,
                              "socios": stmt.excluded.socios},
                    )
                )  # fmt: skip
                session.commit()  # aos poucos: uma interrupção não perde o que já foi feito
                ligados_total += len(ligados)
                if i % 100 == 0:
                    print(f"  {i} de {len(pendentes)}; {ligados_total} sócios ligados", flush=True)
        ingestao = session.merge(ingestao)
        ingestao.registros = session.scalar(select(func.count()).select_from(SocioPessoa))
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now()
        session.commit()
    print(f"  {ligados_total} sócios ligados nesta execução; {falhas} CNPJs sem resposta")
    return ligados_total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    print(f"{FONTE}: {executar()} sócios ligados")
