"""Assembleia Legislativa de Sergipe (ALESE): deputados em exercício e presença em plenário,
pelo site da Casa e pelo Processo Legislativo (SPL).

- Deputados: `al.se.leg.br/deputados/` (24 cartões com nome, partido, foto e o código do
  perfil no SPL).
- Presença: a ficha de cada deputado no SPL (`aleselegis.al.se.leg.br/spl/parlamentar.aspx?id=`)
  traz a aba "Frequência em Plenário" com os totais do ano corrente (presente, falta, falta
  justificada, licenciado, afastado). Sessões = presenças + faltas (justificadas ou não);
  licença e afastamento não contam, o deputado não era esperado em plenário.

Não entram proposições: a consulta do SPL é uma página ASP.NET que só responde por envio de
formulário com estado de sessão (`__VIEWSTATE`), sem rota de listagem. Os `robots.txt` do site e
do SPL liberam tudo. Uma requisição por vez, com pausa. Ver docs/DECISOES.md.
"""

import argparse
import re
import time
from datetime import date

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alese"
SITE = "https://al.se.leg.br/deputados/"
SPL = "https://aleselegis.al.se.leg.br/spl/"
PAUSA = 1.0
CARTAO = re.compile(
    r'<a href="https://aleselegis\.al\.se\.leg\.br/spl/parlamentar\.aspx\?id=(?P<id>\d+)"[^>]*>\s*'
    r'<img[^>]*?\ssrc="(?P<foto>[^"]*)"[^>]*>.*?'
    r'qodef-item-title">\s*<a[^>]*>\s*(?P<nome>[^<]*?)\s*</a>.*?'
    r"qodef-ptf-category-holder\"><span>(?P<partido>[^<]*)</span>",
    re.S,
)
FREQUENCIA = re.compile(
    r"kt-widget1__title'>(?P<situacao>[^<]+)</h3>.*?<big[^>]*>(?P<ano>\d{4})</big>\s*"
    r"<span[^>]*>(?P<n>\d+)</span>",
    re.S,
)


def deputados(pagina: str) -> list[dict]:
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c["id"] in vistos:
            continue
        vistos.add(c["id"])
        resultado.append(
            {
                "id": c["id"],
                "nome": base.limpo(c["nome"]),
                "partido": base.limpo(c["partido"]) or None,
                "foto": c["foto"],
            }
        )
    return resultado


def frequencia(ficha: str, ano: int) -> tuple[int | None, int | None]:
    """(sessões, presenças) no ano, da aba de frequência da ficha; (None, None) sem dados."""
    aba = ficha.split('id="tab_frequencia_plenario"')[-1]
    total: dict[str, int] = {}
    for m in FREQUENCIA.finditer(aba):
        if int(m["ano"]) == ano:
            total[comum.chave_nome(m["situacao"])] = int(m["n"])
    presencas = total.get("PRESENTE", 0)
    sessoes = presencas + total.get("FALTA", 0) + total.get("FALTA JUSTIFICADA", 0)
    return (sessoes, presencas) if sessoes else (None, None)


def coletar(hoje: date) -> dict:
    registros = []
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, SITE, None, 4).content.decode("utf-8", "replace"))
        for d in lista:
            time.sleep(PAUSA)
            try:
                ficha = comum._get(client, f"{SPL}parlamentar.aspx", {"id": d["id"]}, 3)
                sessoes, presencas = frequencia(ficha.content.decode("utf-8", "replace"), hoje.year)
            except Exception as erro:  # uma ficha fora do ar não derruba a lista
                print(f"  ficha {d['id']}: {erro.__class__.__name__}", flush=True)
                sessoes = presencas = None
            registros.append(base.registro(d, sessoes=sessoes, presencas=presencas))
    return base.casa(SITE, registros)


def executar() -> int:
    # A ALESE tem 24 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="SE", sigla="ALESE", url=SITE, minimo=20
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
