"""Assembleia Legislativa do Rio Grande do Norte (ALRN): deputados em exercício e proposições de
autoria, pelo site e pela API do portal de Transparência Legislativa.

- Deputados: `al.rn.leg.br/deputados` (24 cartões com nome, partido e foto, e o código do
  perfil) e `api-transparencialegislativa.al.rn.leg.br/elegis-api-transp-legislativa/parlamentar/`,
  a API que o portal de transparência legislativa chama (sem login), que traz os 24 em exercício
  com o código da iniciativa de cada um. A API devolve também o CPF; não o guardamos.
- Proposições: `processo?iniciativa=ID&pagina=N&tamanhoPagina=100`, da mais nova para a mais
  antiga; paramos ao passar do ano anterior. Projetos (lei, lei complementar, emenda à
  Constituição, decreto legislativo e resolução) entram com a ementa; requerimentos, pedidos de
  informação e moções, só como contagem.

- Gastos: a página "Verbas de ressarcimento" (`www.al.rn.leg.br/portal/verbas`) é um formulário
  (mês e deputado, com o `_token` de formulário do próprio site). Sem escolher o mês, a busca
  devolve todas as notas do deputado: data da nota, fornecedor, deputado e valor. Não há tipo de
  gasto, então tudo entra numa categoria só; o fornecedor (pode ser pessoa física) não é guardado.
  Soma por deputado e mês, do ano anterior em diante. Só os deputados da lista de hoje que casam
  por nome exato com o seletor (24 de 47, o resto é ex-deputado) têm a busca feita.

Sem votos nominais por deputado nesta coleta (a rota `ultimas-votacoes` traz só o resultado).
O `robots.txt` do site libera tudo. Uma requisição por vez, com pausa.
"""

import argparse
import html
import io
import re
import time
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx

from app.db import SessionLocal
from ingestion import comum
from ingestion.assembleias import base

FONTE = "alrn"
SITE = "https://al.rn.leg.br/"
LISTA = SITE + "deputados"
VERBAS = "https://www.al.rn.leg.br/portal/verbas"
CATEGORIA_VERBAS = "Verba de ressarcimento (a fonte não detalha o tipo)"
MOTIVO_SEM_DATA = (
    "A nota vem sem data, com data no futuro ou sem valor legível na página, "
    "então não dá para somar por mês"
)
API = "https://api-transparencialegislativa.al.rn.leg.br/elegis-api-transp-legislativa/"
PAUSA = 1.0
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PR": "Projeto de Resolução",
}
CONTAGEM = {"REQ": "Requerimento", "REQINFOR": "Pedido de Informação", "MOC": "Moção"}
CARTAO = re.compile(
    r'deputado/(?P<id>\d+)/[a-z0-9-]+"[^>]*>.*?url\(\'(?P<foto>[^\']*)\'\).*?'
    r'name-deputies">(?P<nome>[^<]*)</strong>\s*<p class="party-deputies">(?P<partido>[^<]*)</p>',
    re.S,
)


def deputados(pagina: str) -> list[dict]:
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c["id"] in vistos:
            continue
        vistos.add(c["id"])
        sigla = re.search(r"\(([^)]+)\)\s*$", html.unescape(c["partido"]))
        resultado.append(
            {
                "id": c["id"],
                "nome": html.unescape(c["nome"]).strip(),
                "partido": sigla.group(1) if sigla else None,
                "foto": c["foto"],
            }
        )
    return resultado


def iniciativas(cadastro: list[dict]) -> dict[str, int]:
    """Chave do nome parlamentar ('DEPUTADO FULANO' sem o tratamento) -> id da iniciativa."""
    resultado = {}
    for p in cadastro:
        ativa = [i["id"] for i in p.get("iniciativas", []) if i["tipo"] == "PARLAMENTAR"]
        nome = re.sub(r"^DEPUTAD[OA]\s+", "", p["nomeParlamentar"].strip())
        if ativa:
            resultado[comum.chave_nome(nome)] = ativa[-1]
    return resultado


def classificar(processos: list[dict]) -> tuple[dict[str, int], list[dict]]:
    tipos: dict[str, int] = {}
    projetos = []
    for p in processos:
        prop = p.get("propositura") or {}
        sigla = ((prop.get("tipo") or {}).get("sigla") or "").strip()
        if sigla not in PROJETOS and sigla not in CONTAGEM:
            continue
        tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        tipos[tipo] = tipos.get(tipo, 0) + 1
        if sigla in PROJETOS:
            projetos.append(
                base.projeto(
                    sigla,
                    tipo,
                    prop["numero"],
                    int(prop["ano"]),
                    p.get("ementa") or "",
                    (p.get("dataEntrada") or "")[:10] or None,
                    f"{API}processo/{p['id']}",
                )
            )
    return tipos, projetos


def baixar_processos(client, iniciativa: int, desde: int) -> list[dict]:
    resultado, pagina = [], 0
    while True:
        time.sleep(PAUSA)
        d = comum.get_json(
            client,
            API + "processo",
            {"pagina": pagina, "tamanhoPagina": 100, "iniciativa": iniciativa},
            4,
        )
        lote = d.get("dados") or []
        resultado += [p for p in lote if int(p["ano"]) >= desde]
        pagina += 1
        if not lote or int(lote[-1]["ano"]) < desde or len(resultado) >= int(d.get("total") or 0):
            return resultado


def seletor_de_deputados(pagina: str) -> list[tuple[str, str]]:
    """(código, nome) das opções do seletor de deputados da página de verbas (inclui
    ex-deputados)."""
    depois = pagina.split('name="deputado_id"', 1)[-1]
    return [
        (codigo, " ".join(html.unescape(nome).split()))
        for codigo, nome in re.findall(r'<option\s+value="(\d+)"\s*>([^<]+)</option>', depois)
    ]


def notas_da_busca(pagina: str) -> list[dict]:
    """Data da nota e valor de cada linha da tabela de resultados. Fornecedor e nome do
    deputado ficam de fora de propósito. Data ou valor ilegível vira None."""
    resultado = []
    for linha in re.findall(r"<tr><!-- linha da tabela -->(.*?)</tr>", pagina, flags=re.S):
        celulas = [" ".join(c.split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", linha, re.S)]
        if len(celulas) < 4:
            continue
        data = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", celulas[0])
        try:
            quando = date(int(data[3]), int(data[2]), int(data[1])) if data else None
        except ValueError:
            quando = None
        try:
            valor = Decimal(celulas[3]).quantize(Decimal("0.01"))
        except InvalidOperation:
            valor = None
        resultado.append({"data": quando, "valor": valor})
    return resultado


def somar_notas(
    notas: list[dict], desde: int, ate: date | None = None
) -> tuple[list[dict], list[dict]]:
    """Gastos por ano e mês (do ano `desde` em diante) e, à parte, as notas sem data, com data
    no futuro (depois de `ate`, erro de digitação na fonte: há uma de 2029) ou sem valor
    legível. Essas vão por ano da nota; sem data ou no futuro, no ano de `ate` (ou `desde`)."""
    soma: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    fora: dict[int, dict] = {}
    for n in notas:
        futura = ate is not None and n["data"] is not None and n["data"] > ate
        if n["data"] is not None and n["valor"] is not None and not futura:
            if n["data"].year >= desde:
                soma[(n["data"].year, n["data"].month)] += n["valor"]
            continue
        ano = n["data"].year if n["data"] and not futura else (ate.year if ate else desde)
        if ano < desde:
            continue
        acc = fora.setdefault(ano, {"linhas": 0, "valor": Decimal(0), "linhas_valor_ilegivel": 0})
        acc["linhas"] += 1
        if n["valor"] is None:
            acc["linhas_valor_ilegivel"] += 1
        else:
            acc["valor"] += n["valor"]
    gastos = [
        {"ano": a, "mes": m, "categoria": CATEGORIA_VERBAS, "valor": v}
        for (a, m), v in sorted(soma.items())
    ]
    fora_lista = [{"ano": a, "motivo": MOTIVO_SEM_DATA, **d} for a, d in sorted(fora.items())]
    return gastos, fora_lista


def baixar_verbas(client, pagina: str, codigos: list[str]) -> dict[str, bytes]:
    """A página do formulário e, por deputado, a busca sem mês (todas as notas). O `_token` é
    o do formulário da própria página, na mesma sessão (cookie)."""
    token = re.search(r'name="_token" value="([^"]+)"', pagina)
    if not token:
        raise ValueError("ALRN: formulário de verbas sem _token; a página mudou.")
    arquivos = {"formulario.html": pagina.encode("utf-8")}
    for codigo in codigos:
        time.sleep(PAUSA)
        resposta = client.post(
            VERBAS + "/busca",
            data={"_token": token.group(1), "mes_id": "", "deputado_id": codigo},
        )
        arquivos[f"{codigo}.html"] = resposta.raise_for_status().content
    return arquivos


def empacotar(arquivos: dict[str, bytes]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in sorted(arquivos.items()):
            z.writestr(nome, conteudo)
    return memoria.getvalue()


def gastos_dos_deputados(
    client,
    lista: list[dict],
    tse: list[tuple[str, str]],
    desde: int,
    de_raw: Path | None,
    ate: date | None = None,
) -> tuple[dict[str, tuple[list[dict], list[dict]]], list[str]]:
    """id do deputado na lista da Casa -> (gastos, fora) e as mensagens de aviso. A busca só é
    feita para quem casa por nome exato com o seletor ou foi aceito na revisão
    (ver `base.ligar_nomes`)."""
    if de_raw:
        with zipfile.ZipFile(de_raw) as z:
            arquivos = {n: z.read(n) for n in z.namelist()}
        pagina = arquivos["formulario.html"].decode("utf-8", "replace")
    else:
        pagina = comum._get(client, VERBAS, None, 4).text
        arquivos = {}
    seletor = seletor_de_deputados(pagina)
    totais = {comum.chave_nome(n): (1, Decimal(0)) for _, n in seletor}  # valor só após a busca
    ligados, sobras = base.ligar_nomes(FONTE, totais, lista, tse)
    codigos = [c for c, n in seletor if comum.chave_nome(n) in ligados]
    if not de_raw:
        arquivos = baixar_verbas(client, pagina, codigos)
        raw = comum.salvar_raw(FONTE, empacotar(arquivos), "verbas_", ".zip")
        print(f"  bruto das verbas: {raw}", flush=True)
    por_deputado: dict[str, list[dict]] = defaultdict(list)
    nome_por_id = {d["nome"]: d["id"] for d in lista}
    for codigo, nome in seletor:
        alvo = ligados.get(comum.chave_nome(nome))
        if alvo and f"{codigo}.html" in arquivos:
            texto = arquivos[f"{codigo}.html"].decode("utf-8", "replace")
            por_deputado[nome_por_id[alvo]] += notas_da_busca(texto)
    if not por_deputado or not any(por_deputado.values()):
        raise ValueError("ALRN: nenhuma nota de verba lida; abortando para não zerar os gastos.")
    avisos = []
    sem_busca = [n for _, n in seletor if comum.chave_nome(n) not in ligados]
    if sem_busca:
        avisos.append(
            f"Gastos ALRN: {len(sem_busca)} nomes do seletor de verbas sem deputado igual na "
            "lista de hoje (ex-deputados ou grafia diferente), sem busca: " + "; ".join(sem_busca)
        )
    return {i: somar_notas(n, desde, ate) for i, n in por_deputado.items()}, avisos


def gastos_anteriores(session: Any) -> dict[str, tuple[list[dict], list[dict]]]:
    """Gastos já gravados, por id do deputado na Casa: (gastos, fora). Servem para não zerar
    os gastos quando a fonte das verbas está fora do ar ou exige credencial."""
    from sqlalchemy import select

    from app.models import GastoLocal, GastoLocalFora, MandatoLocal

    mandatos = {
        m.id: m.id_externo
        for m in session.scalars(
            select(MandatoLocal).where(MandatoLocal.casa == "assembleia", MandatoLocal.uf == "RN")
        )
    }
    resultado: dict[str, tuple[list[dict], list[dict]]] = {i: ([], []) for i in mandatos.values()}
    for g in session.scalars(select(GastoLocal).where(GastoLocal.mandato_id.in_(mandatos))):
        resultado[mandatos[g.mandato_id]][0].append(
            {"ano": g.ano, "mes": g.mes, "categoria": g.categoria, "valor": g.valor}
        )
    for f in session.scalars(select(GastoLocalFora).where(GastoLocalFora.mandato_id.in_(mandatos))):
        resultado[mandatos[f.mandato_id]][1].append(
            {"ano": f.ano, "linhas": f.linhas, "valor": f.valor, "motivo": f.motivo,
             "linhas_valor_ilegivel": f.linhas_valor_ilegivel}
        )  # fmt: skip
    return resultado


def gastos_ou_anteriores(client, lista, tse, hoje: date, de_raw: Path | None):
    """Os gastos da fonte; se ela não responder (404, 401, rede), devolve os já gravados e um
    aviso para `fonte_ingestao`. Não trata a falha como "sem gastos"."""
    try:
        return gastos_dos_deputados(client, lista, tse, hoje.year - 1, de_raw, hoje)
    except (httpx.HTTPStatusError, httpx.TransportError) as erro:
        with SessionLocal() as session:
            gastos = gastos_anteriores(session)
        aviso = (
            f"Gastos ALRN: a fonte das verbas não respondeu ({erro.__class__.__name__}: "
            f"{str(erro)[:120]}); mantidos os gastos da carga anterior, sem atualização"
        )
        return gastos, [aviso]


def coletar(hoje: date, de_raw: Path | None = None) -> tuple[dict, list[str]]:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        with SessionLocal() as session:
            tse = base.nomes_do_tse(session, "RN")
        gastos, avisos = gastos_ou_anteriores(client, lista, tse, hoje, de_raw)
        ids = iniciativas(comum.get_json(client, API + "parlamentar/").get("dados", []))
        registros = []
        for d in lista:
            g, fora = gastos.get(d["id"]) or gastos.get(str(d["id"])) or ([], [])
            iniciativa = ids.get(comum.chave_nome(d["nome"]))
            if iniciativa is None:
                print(f"  {d['nome']}: sem iniciativa na API; entra sem proposições", flush=True)
                registros.append(base.registro(d, gastos=g, gastos_fora=fora))
                continue
            tipos, projetos = classificar(baixar_processos(client, iniciativa, hoje.year - 1))
            registros.append(
                base.registro(d, projetos=projetos, por_tipo=tipos, gastos=g, gastos_fora=fora)
            )
    return base.casa(LISTA, registros), avisos


def executar(de_raw: Path | None = None) -> int:
    casa, avisos = coletar(date.today(), de_raw)
    for a in avisos:
        print(f"  AVISO {a}", flush=True)
    # A ALRN tem 24 cadeiras: lista curta é falha da fonte.
    return base.gravar(casa, fonte=FONTE, uf="RN", sigla="ALRN", url=API, minimo=20, alertas=avisos)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de verbas de data/raw/alrn (sem rede)")
    executar(ap.parse_args().de_raw)
