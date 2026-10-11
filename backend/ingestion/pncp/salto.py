"""Salto de valor no histórico do PNCP (docs/DECISOES.md, "PNCP: valores suspeitos").

O acervo guarda `pncp_soma` por dia × órgão × fornecedor × tipo, sem o valor inicial, então a
regra "valor global maior que 100 vezes o inicial" (`suspeito.py`) não se aplica às somas
antigas. Para o que aparece no site, relê-se a API só onde importa:

- candidatos: linhas de `pncp_soma` de órgão municipal, a partir do ano anterior, com valor
  de R$ 10 milhões ou mais, de um fornecedor que está entre os 30 maiores do município no ano
  (`pncp_anual`) ou na janela (`pncp_janela`) do pacote;
- para cada órgão × dia de publicação dos candidatos, uma consulta à API (filtro `cnpjOrgao`,
  uma requisição por vez, com pausa) e a regra em cada contrato lido;
- o resultado vai para um JSON retomável (`verificados` evita repetir consulta), que o
  `pacote gerar --saltos` usa: o contrato sai das somas e entra em `pncp_suspeito`, com o valor
  original, sem corrigir nada.

    python -m ingestion.pncp.salto varrer --url URL_DO_ACERVO --saida saltos.json [--minutos 120]
    python -m ingestion.pncp.salto contar --url URL_DO_ACERVO
"""

import argparse
import json
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ingestion import comum
from ingestion.pncp import contratos, pacote, suspeito

VALOR_MINIMO = Decimal("10000000")  # linha de soma que vale reler (R$ 10 milhões)
PAUSA = 0.5


def candidatos(
    session: Session, hoje: date, minimo: Decimal = VALOR_MINIMO
) -> list[tuple[date, str]]:
    """(dia, órgão) a reler: ver o texto do módulo."""
    t = pacote.montar(session, hoje)
    chaves = {
        (r["municipio_ibge"], r["fornecedor_cnpj"], r["ano"])
        for r in t["pncp_anual"]
        if r["valor_global"] >= minimo
    } | {
        (r["municipio_ibge"], r["fornecedor_cnpj"], r["dia"].year)
        for r in t["pncp_janela"]
        if r["valor_global"] >= minimo
    }
    linhas = session.execute(
        text(
            """
            SELECT p.dia, p.orgao_cnpj, p.municipio_ibge, p.fornecedor_cnpj
            FROM pncp_soma p JOIN pncp_orgao o ON o.cnpj = p.orgao_cnpj AND o.esfera = 'M'
            WHERE p.fornecedor_cnpj <> '' AND p.dia >= :inicio AND p.valor_global >= :minimo
            """
        ),
        {"inicio": date(hoje.year - 1, 1, 1), "minimo": minimo},
    )
    achados = {(dia, org) for dia, org, ibge, forn in linhas if (ibge, forn, dia.year) in chaves}
    # casos conhecidos entram sempre
    for numero, (dia, _) in suspeito.CASOS_CONHECIDOS.items():
        achados.add((date.fromisoformat(dia), numero.split("-")[0]))
    return sorted(achados)


def saltos_do_dia(client: Any, dia: date, orgao: str, limites: Any, pausa: float) -> list[dict]:
    """Contratos municipais do órgão publicados no dia que a regra do salto marca."""
    saida = []
    for corpo, _ in contratos.paginas(client, contratos.URL, dia, pausa, {"cnpjOrgao": orgao}):
        for c in corpo.get("data") or []:
            if (c.get("orgaoEntidade") or {}).get("esferaId") != "M" or c.get("receita"):
                continue
            _, cnpj = contratos.fornecedor_de(c)
            unidade = c.get("unidadeOrgao") or {}
            ibge = contratos._digitos(unidade.get("codigoIbge"))[:7]
            valor = contratos._valor(c.get("valorGlobal"))
            inicial = contratos._valor(c.get("valorInicial"))
            numero = c.get("numeroControlePNCP")
            if not (cnpj and ibge and valor and valor > 0 and numero):
                continue
            if not suspeito.eh_suspeito(valor, "M", ibge, None, inicial, numero):
                continue
            if valor <= suspeito.limite("M", ibge, limites):  # só o que a regra nova pegou
                saida.append({
                    "numero": numero, "dia": dia.isoformat(), "orgao_cnpj": orgao,
                    "municipio_ibge": ibge, "fornecedor_cnpj": cnpj,
                    "tipo_contrato": contratos._nome(c.get("tipoContrato")),
                    "valor_inicial": str(inicial if inicial is not None else 0),
                    "valor_global": str(valor),
                })  # fmt: skip
    return saida


def varrer(
    session: Session,
    saida: Path,
    minutos: float,
    hoje: date,
    pausa: float = PAUSA,
    minimo: Decimal = VALOR_MINIMO,
) -> dict[str, int]:
    estado: dict[str, Any] = {"verificados": [], "saltos": []}
    if saida.exists():
        estado = json.loads(saida.read_text(encoding="utf-8"))
    feitos = set(estado["verificados"])
    lista = candidatos(session, hoje, minimo)
    limites = suspeito.carregar_limites(session)
    fim = time.monotonic() + minutos * 60
    consultas = 0
    with comum.criar_cliente() as client:
        for dia, orgao in lista:
            chave = f"{orgao}|{dia.isoformat()}"
            if chave in feitos:
                continue
            if time.monotonic() > fim:
                break
            achados = saltos_do_dia(client, dia, orgao, limites, pausa)
            novos = {x["numero"]: x for x in estado["saltos"]}
            novos.update({x["numero"]: x for x in achados})
            estado["saltos"] = sorted(novos.values(), key=lambda x: x["numero"])
            estado["verificados"].append(chave)
            consultas += 1
            if consultas % 25 == 0:
                saida.write_text(json.dumps(estado), encoding="utf-8")
                print(f"  {len(estado['verificados'])}/{len(lista)} saltos={len(estado['saltos'])}",
                      flush=True)  # fmt: skip
            time.sleep(pausa)
    saida.write_text(json.dumps(estado), encoding="utf-8")
    return {"candidatos": len(lista), "verificados": len(estado["verificados"]),
            "saltos": len(estado["saltos"])}  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description="Salto de valor no histórico do PNCP")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome in ("varrer", "contar"):
        p = sub.add_parser(nome)
        p.add_argument("--url", required=True, help="URL do acervo (só SELECT)")
        p.add_argument("--hoje", type=date.fromisoformat, default=date.today())
        p.add_argument("--minimo", type=Decimal, default=VALOR_MINIMO, help="valor mínimo da linha")
    v = sub.choices["varrer"]
    v.add_argument("--saida", type=Path, required=True)
    v.add_argument("--minutos", type=float, default=120)
    v.add_argument("--pausa", type=float, default=PAUSA)
    args = parser.parse_args()
    with sessionmaker(bind=create_engine(args.url))() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        if args.comando == "contar":
            print(len(candidatos(session, args.hoje, args.minimo)), "consultas")
        else:
            print(
                json.dumps(
                    varrer(session, args.saida, args.minutos, args.hoje, args.pausa, args.minimo)
                )
            )


if __name__ == "__main__":
    main()
