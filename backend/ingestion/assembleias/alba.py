"""Assembleia Legislativa da Bahia (ALBA): deputados no cargo hoje, proposições de autoria e
presença em plenário, pela API pública de dados abertos do Processo Legislativo Eletrônico
(albalegis.nopapercloud.com.br/dados-abertos.aspx).

- `/api/publico/parlamentar/`: os deputados (nome, nome civil, partido, foto, e-mail,
  situação) e, para cada um, a frequência em plenário por ano (presente, falta, falta
  justificada, licença...).
- `/api/publico/proposicao/?ano=AAAA`: todas as proposições do ano, com tipo, ementa, data,
  situação e o autor. Projetos (lei, lei complementar, emenda à Constituição, decreto
  legislativo e resolução) são guardados com a ementa; indicações, moções, requerimentos e
  utilidade pública entram só como contagem.

A API não publica votos nominais nem verba de gabinete. Uma requisição por vez, com pausa.
Grava nas mesmas tabelas das outras casas, pela gravação do conector SAPL.
"""

import argparse
import time
from datetime import UTC, date, datetime
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alba"
SITE = "https://albalegis.nopapercloud.com.br/"
API = SITE + "api/publico/"
PAUSA = 1.0
POR_PAGINA = 100
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PRS": "Projeto de Resolução",
}
CONTAGEM = {
    "IND": "Indicação",
    "MOC": "Moção",
    "REQ": "Requerimento",
    "UP": "Utilidade Pública",
}


def deputados(resposta: dict) -> list[dict[str, Any]]:
    """Os deputados em exercício da legislatura vigente (situação 'Ativo')."""
    ativos = [
        p for p in resposta.get("parlamentares", []) if p.get("parlamentarSituacao") == "Ativo"
    ]
    legislatura = max((int(p["parlamentarLegislatura"]) for p in ativos), default=None)
    return [p for p in ativos if int(p["parlamentarLegislatura"]) == legislatura]


def frequencia(deputado: dict, anos: set[int]) -> tuple[int | None, int | None]:
    """(sessões, presenças) nos anos pedidos: sessões = presenças + faltas (justificadas ou
    não). Licenças e afastamentos não contam, o deputado não era esperado em plenário."""
    por_situacao: dict[str, int] = {}
    for grupo in deputado.get("frequenciaPlenario") or []:
        total = sum(
            int(a["quantidade"] or 0)
            for a in grupo.get("frequenciaSituacaoAnos", [])
            if int(a["ano"]) in anos
        )
        por_situacao[comum.chave_nome(grupo["frequenciaSituacaoNome"])] = total
    presencas = por_situacao.get("PRESENTE", 0)
    sessoes = presencas + por_situacao.get("FALTA", 0) + por_situacao.get("FALTA JUSTIFICADA", 0)
    return (sessoes, presencas) if sessoes else (None, None)


def _data(valor: str | None) -> str | None:
    try:
        return datetime.strptime((valor or "").strip()[:10], "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(props: list[dict], parlamentares: list[dict]) -> dict[str, dict]:
    """Id do deputado -> contagem por tipo e projetos de autoria. O autor vem pelo nome civil
    (o mesmo que a lista de deputados traz como razão social)."""
    por_nome = {comum.chave_nome(p["parlamentarRazaoSocial"]): p for p in parlamentares}
    por_autor = {str(p["autorID"]): p for p in parlamentares if p.get("autorID")}
    resultado = {str(p["parlamentarID"]): {"contagem": {}, "projetos": []} for p in parlamentares}
    for p in props:
        autor = p.get("AutorRequerenteDados") or {}
        dono = por_nome.get(comum.chave_nome(autor.get("nomeRazao"))) or por_autor.get(
            str(autor.get("autorId"))
        )
        sigla = (p.get("sigla") or "").strip()
        if dono is None or (sigla not in PROJETOS and sigla not in CONTAGEM):
            continue
        tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        dep = resultado[str(dono["parlamentarID"])]
        dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
        if sigla in PROJETOS:
            situacao = (p.get("situacao") or "").strip().upper()
            dep["projetos"].append(
                {
                    "id_externo": f"{sigla}-{p['numero']}-{p['ano']}"[:20],
                    "tipo": tipo,
                    "numero": int(p["numero"]) if str(p.get("numero")).isdigit() else None,
                    "ano": int(p["ano"]),
                    "ementa": " ".join((p.get("assunto") or "").split()),
                    "data_apresentacao": _data(p.get("data")),
                    "em_tramitacao": situacao == "TRAMITANDO" if situacao else None,
                    "primeiro_autor": True,
                    "url": p.get("arquivo")
                    or f"{API}proposicao/?processo={p.get('processo')}&ano={p['ano']}",
                }
            )
    return resultado


def baixar_proposicoes(client: Any, ano: int) -> list[dict]:
    """Todas as proposições do ano, 100 por página, uma requisição por vez."""
    resultado, pagina = [], 1
    while True:
        time.sleep(PAUSA)
        dados = comum.get_json(
            client, API + "proposicao/", {"pag": pagina, "qtd": POR_PAGINA, "ano": ano}, 4
        )
        resultado += dados.get("Data") or []
        if pagina >= int(dados.get("Paginacao", {}).get("quantidade") or 0):
            return resultado
        pagina += 1


def coletar(hoje: date) -> dict:
    anos = {hoje.year - 1, hoje.year}
    with comum.criar_cliente() as client:
        lista = deputados(comum.get_json(client, API + "parlamentar/", {"pag": 1, "qtd": 200}))
        props = []
        for ano in sorted(anos):
            props += baixar_proposicoes(client, ano)
    autoria = distribuir(props, lista)
    vereadores = []
    for d in lista:
        sessoes, presencas = frequencia(d, anos)
        dep = autoria[str(d["parlamentarID"])]
        vereadores.append(
            {
                "id_externo": str(d["parlamentarID"]),
                "nome": d["parlamentarNome"].strip(),
                "nome_completo": comum.nome_proprio((d.get("parlamentarRazaoSocial") or "").strip())
                or None,
                "partido": d.get("partidoSigla") or None,
                "foto_url": d.get("parlamentarFoto") or None,
                "email": (d.get("parlamentarEmail") or "").strip().lower() or None,
                "telefone": (d.get("parlamentarTelefone") or "").strip() or None,
                "titular": True,
                "em_exercicio": True,
                "inicio": None,
                "fim": None,
                "proposicoes_por_tipo": dep["contagem"],
                "projetos": dep["projetos"],
                "sessoes": sessoes,
                "presencas": presencas,
            }
        )
    return {
        "base": SITE,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 50:  # a ALBA tem 63 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALBA; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="BA")
        session.add(
            FonteIngestao(fonte=FONTE, url=API, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALBA: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
