"""Câmaras municipais no portal legislativo da Cittatec (Citta Conecta): vereadores da
legislatura atual e a contagem de proposições de cada um.

Várias câmaras que saíram do SAPL migraram para este sistema (Pelotas, Erechim, São Borja,
Ronda Alta, Barra do Ribeiro, Palminópolis). O portal é uma aplicação Angular em
`cm<cidade>.cittatec.com.br`; os dados vêm de uma API JSON pública, a mesma que a página usa:

- `/api/conecta/public/clientes/<base64 do nome>/tenant`: o identificador da câmara (o
  cabeçalho `ID-Tenant` das demais chamadas), que é o próprio nome do subdomínio;
- `/api/open-data-leg/public/legislaturas`: a lista de legislaturas (uma é a atual);
- `/api/open-data-leg/public/parlamentares/legislaturas/<id>`: um registro por período de
  exercício (titular ou suplente que assumiu), com nome de urna, nome civil, partido, foto,
  e-mail, datas e se está ativo hoje;
- `/api/open-data-leg/public/mandatos/proposicoes/parlamentares/<pessoa>`: quantas
  proposições o vereador apresentou, por tipo, num período.

A API não publica o texto de cada projeto, votos nominais nem presença: a câmara entra com
vereadores e a contagem de proposições. Os endereços vêm do catálogo versionado de canais
(tipo "sistema_legislativo", sistema "cittatec"). Uma requisição por vez, com pausa.
Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao eleito do TSE).
"""

import argparse
import base64
import re
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.canais import catalogo

FONTE = "cittatec_camaras"
SISTEMA = "cittatec"
PAUSA = 0.5
# Itens que o sistema lista junto das proposições mas não são proposição de autoria do
# vereador: pareceres de comissão, memorandos, recursos e justificativas de ausência.
NAO_PROPOSICAO = re.compile(r"^(parecer|memorando|recurso|justificativa de aus)", re.I)
ENDERECO = re.compile(r"^https?://(?P<tenant>[a-z0-9-]+)\.cittatec\.com\.br", re.I)


class Cittatec:
    def __init__(self, tenant: str, client: httpx.Client) -> None:
        self.tenant = tenant
        self.base = f"https://{tenant}.cittatec.com.br"
        self.client = client
        client.headers["ID-Tenant"] = tenant

    def get(self, caminho: str, **params: Any) -> Any:
        time.sleep(PAUSA)
        return comum.get_json(
            self.client,
            f"{self.base}/api/{caminho}",
            params=params or None,
        )

    @property
    def portal(self) -> str:
        return f"{self.base}/portal-legislativo/vereadores"


def tenant_de(url: str) -> str | None:
    achado = ENDERECO.match(url)
    return achado["tenant"].lower() if achado else None


def legislatura_atual(legislaturas: list[dict], hoje: date) -> dict | None:
    """A legislatura marcada como atual pelo sistema e que cobre a data de hoje (com 90 dias
    de folga depois do fim, para a transição). Sem ela, a câmara não mantém o cadastro."""
    adequadas = [
        lg
        for lg in legislaturas
        if lg.get("legislaturaAtual")
        and date.fromisoformat(lg["dataInicio"])
        <= hoje
        <= date.fromisoformat(lg["dataFim"]) + timedelta(days=90)
    ]
    return max(adequadas, key=lambda lg: lg["dataInicio"]) if adequadas else None


def _dia(valor: str | None) -> str | None:
    return valor[:10] if valor else None


def _limpo(texto: str | None) -> str:
    return " ".join((texto or "").split())


def vereadores(registros: list[dict]) -> list[dict]:
    """Junta os períodos de exercício da mesma pessoa em um vereador. Está em exercício se
    algum período está ativo; é titular se algum período não é de substituição."""
    por_pessoa: dict[int, list[dict]] = {}
    for r in registros:
        por_pessoa.setdefault(r["pessoa"]["id"], []).append(r)
    lista = []
    for pessoa_id, periodos in por_pessoa.items():
        ativos = [p for p in periodos if p.get("ativo")]
        referencia = (ativos or periodos)[-1]
        pessoa = referencia["pessoa"]
        partido = (referencia.get("partido") or {}).get("sigla")
        lista.append(
            {
                "id_externo": str(pessoa_id),
                "nome": _limpo(referencia.get("parlamentar") or pessoa.get("nome")),
                "nome_completo": _limpo(pessoa.get("nome")) or None,
                "partido": partido,
                "foto_url": None,  # o endereço da foto embute o CPF (em base64): não guardamos
                "email": _limpo(pessoa.get("email")) or None,
                "telefone": _limpo(pessoa.get("fone"))[:60] or None,
                "titular": any(not p.get("evento") for p in periodos),
                "em_exercicio": bool(ativos),
                "inicio": min(_dia(p["dataInicio"]) for p in periodos),
                "fim": max(
                    _dia((p.get("mandato") or {}).get("dataFim") or p["dataFim"]) for p in periodos
                ),
                "proposicoes_por_tipo": {},
                "projetos": [],
            }
        )
    return lista


def contagem_de_proposicoes(itens: list[dict]) -> dict[str, int]:
    """'PROJETO DE LEI ORDINÁRIA' vira 'Projeto de lei ordinária', como nos outros conectores."""
    resultado: dict[str, int] = {}
    for item in itens:
        nome = _limpo(item.get("nomeProposicao")).capitalize()
        if nome and item.get("quantidade") and not NAO_PROPOSICAO.match(nome):
            resultado[nome] = resultado.get(nome, 0) + int(item["quantidade"])
    return resultado


def coletar(url: str, hoje: date) -> dict | None:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto). None se o sistema
    não tem legislatura em vigor."""
    nome = tenant_de(url)
    if nome is None:
        raise ValueError(f"Endereço fora do padrão da Cittatec: {url}")
    with comum.criar_cliente() as client:
        cliente = Cittatec(nome, client)
        # O identificador da câmara vem do próprio sistema (a página faz o mesmo).
        id_cliente = base64.b64encode(nome.encode()).decode()
        time.sleep(PAUSA)
        resposta = comum.get_json(
            client, f"{cliente.base}/api/conecta/public/clientes/{id_cliente}/tenant"
        )
        cliente.client.headers["ID-Tenant"] = resposta.get("ID-Tenant") or nome
        legislatura = legislatura_atual(cliente.get("open-data-leg/public/legislaturas"), hoje)
        if legislatura is None:
            return None
        registros = cliente.get(
            f"open-data-leg/public/parlamentares/legislaturas/{legislatura['id']}"
        )
        lista = vereadores(registros)
        # Proposições do ano anterior e do atual, como no SAPL.
        periodo = [f"{hoje.year - 1}-01-01T00:00:00", f"{hoje.year}-12-31T23:59:59"]
        for v in lista:
            try:
                itens = cliente.get(
                    f"open-data-leg/public/mandatos/proposicoes/parlamentares/{v['id_externo']}",
                    periodoMandato=",".join(periodo),
                )
            except httpx.HTTPStatusError as erro:
                if erro.response.status_code >= 500 or erro.response.status_code in (400, 404):
                    print(
                        f"  {cliente.base}: proposições de {v['nome']} não lidas "
                        f"({erro.response.status_code})",
                        flush=True,
                    )
                    continue
                raise
            v["proposicoes_por_tipo"] = contagem_de_proposicoes(itens)
    return {"base": cliente.portal, "legislatura": legislatura, "vereadores": lista}


def executar(limite: int | None = None) -> int:
    camaras = [
        (c["municipio_ibge"], c["url"])
        for c in catalogo.ler()
        if c["tipo"] == "sistema_legislativo" and c["sistema"] == SISTEMA
    ]
    camaras = camaras[:limite] if limite else camaras
    hoje = date.today()
    total, falhas = 0, 0
    for ibge, url in camaras:
        try:
            camara = coletar(url, hoje)
            with SessionLocal() as session:
                if camara is None:
                    if sapl.esquecer(session, ibge, None):
                        print(f"  {url}: sem legislatura em vigor; dados antigos removidos")
                elif not camara["vereadores"]:
                    raise ValueError("lista de vereadores vazia")
                else:
                    total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {url}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="portais legislativos Cittatec das câmaras do catálogo data/canais_curados.csv",
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(f"{len(camaras)} câmaras, {falhas} com falha, {total} vereadores", flush=True)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--limite", type=int, help="Só as N primeiras câmaras (teste)")
    args = parser.parse_args()
    executar(args.limite)
