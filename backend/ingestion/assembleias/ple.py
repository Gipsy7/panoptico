"""Processo Legislativo Eletrônico (PLE, da Nopapercloud): a API pública de dados abertos que
mais de uma assembleia usa (ALBA e ALES), com o mesmo desenho em `/api/publico/`.

- `parlamentar/`: os deputados (nome, nome civil, partido, foto, e-mail, situação) e, para
  cada um, a frequência em plenário por ano (presente, falta, falta justificada, licença...).
- `proposicao/?ano=AAAA`: as proposições do ano, com tipo, ementa, data, situação e o autor.
  Projetos são guardados com a ementa; os tipos de `contagem` entram só como contagem.

Cada assembleia é um conector fino (`alba.py`, `ales.py`) que diz o endereço da API, as siglas
de cada tipo e a UF. Daqui vem a lógica comum. A API não publica votos nominais nem verba de
gabinete. Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas,
pela gravação do conector SAPL.
"""

import time
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

POR_PAGINA = 100


def deputados(resposta: dict) -> list[dict[str, Any]]:
    """Os deputados em exercício da legislatura vigente. A situação vem como 'Ativo' (ALBA)
    ou 'Ativos' (ALES); suplentes que não assumiram e titulares que saíram têm outro texto."""
    ativos = [
        p
        for p in resposta.get("parlamentares", [])
        if comum.chave_nome(p.get("parlamentarSituacao")) in ("ATIVO", "ATIVOS")
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
    # A ALBA diz "Falta" e "Falta Justificada"; a ALES, "Ausência" e "Ausência Justificada".
    faltas = sum(
        por_situacao.get(s, 0)
        for s in ("FALTA", "FALTA JUSTIFICADA", "AUSENCIA", "AUSENCIA JUSTIFICADA")
    )
    sessoes = presencas + faltas
    return (sessoes, presencas) if sessoes else (None, None)


def _data(valor: str | None) -> str | None:
    try:
        return datetime.strptime((valor or "").strip()[:10], "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(
    props: list[dict],
    parlamentares: list[dict],
    api: str,
    projetos: Mapping[str, str],
    contagem: Mapping[str, str],
) -> dict[str, dict]:
    """Id do deputado -> contagem por tipo e projetos de autoria. O autor vem pelo nome civil
    (o mesmo que a lista de deputados traz como razão social) ou pelo id de autor."""
    por_nome = {comum.chave_nome(p["parlamentarRazaoSocial"]): p for p in parlamentares}
    por_autor = {str(p["autorID"]): p for p in parlamentares if p.get("autorID")}
    resultado = {str(p["parlamentarID"]): {"contagem": {}, "projetos": []} for p in parlamentares}
    for p in props:
        autor = p.get("AutorRequerenteDados") or {}
        dono = por_nome.get(comum.chave_nome(autor.get("nomeRazao"))) or por_autor.get(
            str(autor.get("autorId"))
        )
        sigla = (p.get("sigla") or "").strip()
        if dono is None or (sigla not in projetos and sigla not in contagem):
            continue
        tipo = projetos.get(sigla) or contagem[sigla]
        dep = resultado[str(dono["parlamentarID"])]
        dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
        if sigla in projetos:
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
                    or f"{api}proposicao/?processo={p.get('processo')}&ano={p['ano']}",
                }
            )
    return resultado


def baixar_proposicoes(
    client: Any, api: str, ano: int, pausa: float, sigla: str | None = None
) -> list[dict]:
    """Todas as proposições do ano (ou só da `sigla`), 100 por página, uma por vez."""
    resultado, pagina = [], 1
    while True:
        time.sleep(pausa)
        params: dict[str, Any] = {"pag": pagina, "qtd": POR_PAGINA, "ano": ano}
        if sigla:
            params["sigla"] = sigla
        dados = comum.get_json(client, api + "proposicao/", params, 4)
        resultado += dados.get("Data") or []
        # A ALBA escreve "Paginacao", a ALES também; "paginacao" na lista de parlamentares.
        paginacao = dados.get("Paginacao") or dados.get("paginacao") or {}
        if pagina >= int(paginacao.get("quantidade") or 0):
            return resultado
        pagina += 1


def coletar(
    hoje: date,
    *,
    site: str,
    api: str,
    pausa: float,
    projetos: Mapping[str, str],
    contagem: Mapping[str, str],
    por_sigla: bool = False,
) -> dict:
    """`por_sigla`: pede à API só os tipos que interessam (a ALES tem milhares de ofícios,
    atas e pautas por ano, que não são proposições de deputado)."""
    anos = {hoje.year - 1, hoje.year}
    with comum.criar_cliente() as client:
        lista = deputados(comum.get_json(client, api + "parlamentar/", {"pag": 1, "qtd": 200}))
        props = []
        for ano in sorted(anos):
            if por_sigla:
                for sigla in (*projetos, *contagem):
                    props += baixar_proposicoes(client, api, ano, pausa, sigla)
            else:
                props += baixar_proposicoes(client, api, ano, pausa)
    autoria = distribuir(props, lista, api, projetos, contagem)
    vereadores = []
    for d in lista:
        sessoes, presencas = frequencia(d, anos)
        dep = autoria[str(d["parlamentarID"])]
        vereadores.append(
            {
                "id_externo": str(d["parlamentarID"]),
                "nome": comum.nome_proprio(d["parlamentarNome"].strip())
                if d["parlamentarNome"].strip().isupper()
                else d["parlamentarNome"].strip(),
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
        "base": site,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def gravar(casa: dict, *, fonte: str, uf: str, sigla: str, url: str, minimo: int) -> int:
    """Grava a casa e registra a carga; recusa lista curta de deputados (falha da fonte)."""
    if len(casa["vereadores"]) < minimo:
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na {sigla}; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf=uf)
        session.add(
            FonteIngestao(fonte=fonte, url=url, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"{sigla}: {total} deputados", flush=True)
    return total
