"""Câmaras municipais no Portal da Transparência da CR2 (portalcr2.com.br): Beruri (AM),
Itamarandiba (MG), Benevides e São Miguel do Guamá (PA). Os sites das câmaras só redirecionam
para o portal da CR2, uma aplicação Bubble que não mostra os dados no HTML.

A CR2 publica uma API de dados abertos (a página "Acesse nossos dados abertos" do portal;
`/api/1.1/meta` lista os tipos de dado, todos de leitura pública). O tipo `parlamentares`
traz um registro por vereador de todas as câmaras que usam o portal (milhares), com nome,
nome civil, partido, foto, e-mail, telefone, se é titular e se está ativo hoje. Uma câmara é
identificada pelo apelido do portal (`cm-beruri`), que é o início ou o fim do `Slug` de cada
vereador (`cm-beruri-gedean-amaro`, `jose-pedro-solon-de-oliveira-cm-benevides`).

Armadilhas encontradas nos dados reais:
- o registro de quem saiu continua lá, com `ativo` falso; vereador cadastrado de novo (outra
  legislatura) aparece duas vezes, uma delas com `deletado` verdadeiro: só entra quem está
  ativo e não apagado, uma vez por pessoa;
- o partido vem em formatos diferentes: "MDB", "Movimento Democrático Brasileiro (MDB)",
  "PDT (Partido Democrático Trabalhista)", e também "Sem partido", "Aguardando Informação"
  e "*" (que não são partido);
- o filtro `contains` da API casa por palavra e não por trecho, então a busca usa a última
  palavra do apelido ("guama") e o resto é conferido aqui.

Matérias legislativas (`materias_legislativas`) são publicadas como pacotes mensais com um
documento anexo e uma lista de autores, não como projetos individuais com número e ementa:
ficam de fora. A API também não traz votos nem presença. Os endereços vêm do catálogo
versionado de canais (tipo "sistema_legislativo", sistema "cr2"). Uma requisição por vez, com
pausa. Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao eleito
do TSE).
"""

import argparse
import json
import re
import time
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.canais import catalogo

FONTE = "cr2_camaras"
SISTEMA = "cr2"
PAUSA = 0.5
API = "https://www.portalcr2.com.br/api/1.1/obj/parlamentares"
PORTAL = "https://www.portalcr2.com.br/parlamentares/parlamentares-{entidade}"
ENDERECO = re.compile(
    r"^https?://(?:www\.)?portalcr2\.com\.br/entidade/(?P<entidade>cm-[a-z0-9-]+)", re.I
)
NAO_E_PARTIDO = {"", "*", "sem partido", "aguardando informação", "aguardando informacao"}


def entidade_de(url: str) -> str | None:
    achado = ENDERECO.match(url)
    return achado["entidade"].lower() if achado else None


def eh_da_camara(slug: str, entidade: str) -> bool:
    return slug.startswith(f"{entidade}-") or slug.endswith(f"-{entidade}")


def partido(texto: str | None) -> str | None:
    """A sigla, de 'MDB', 'Movimento Democrático Brasileiro (MDB)' ou 'PDT (Partido ...)'."""
    texto = " ".join((texto or "").split())
    if texto.lower() in NAO_E_PARTIDO:
        return None
    dentro = re.search(r"\(([^()]*)\)\s*$", texto)
    if dentro:
        sigla = dentro[1].strip()
        # 'PDT (Partido Democrático Trabalhista)': a sigla é o que vem antes dos parênteses.
        return sigla if " " not in sigla else texto[: dentro.start()].strip() or None
    return texto


def _limpo(texto: str | None) -> str:
    return " ".join((texto or "").split())


def _id_curto(id_bubble: str) -> str:
    """O id do Bubble ('1788267633072x485227535643181060', 33 caracteres) não cabe na coluna de
    20: ficam a data de criação em milissegundos e os 6 últimos dígitos do sufixo aleatório."""
    criado, _, sufixo = id_bubble.partition("x")
    return f"{criado}x{sufixo[-6:]}"


def _foto(url: str | None) -> str | None:
    if not url:
        return None
    return f"https:{url}" if url.startswith("//") else url


def vereadores(registros: list[dict], entidade: str) -> list[dict]:
    """Os vereadores ativos da câmara, uma vez por pessoa."""
    por_pessoa: dict[str, dict] = {}
    for r in registros:
        if not eh_da_camara(r.get("Slug") or "", entidade):
            continue
        if not r.get("ativo") or r.get("deletado"):
            continue
        nome = _limpo(r.get("nomeParlamentar") or r.get("nomeCompletoParlamentar"))
        civil = _limpo(r.get("nomeCompletoParlamentar")) or None
        if not nome:
            continue
        chave = comum.chave_nome(civil or nome)
        alterado = r.get("Modified Date") or ""
        anterior = por_pessoa.get(chave)
        # Duplicado: fica o cadastro alterado por último.
        if anterior and anterior["_alterado"] >= alterado:
            continue
        por_pessoa[chave] = {
            "id_externo": _id_curto(r["_id"]),
            "nome": nome,
            "nome_completo": civil if civil and civil != nome else None,
            "partido": partido(r.get("partidoParlamentar")),
            "foto_url": _foto(r.get("fotoParlamentar")),
            "email": _limpo(r.get("emailParlamentar")) or None,
            "telefone": _limpo(r.get("telefoneParlamentar"))[:60] or None,
            "titular": bool(r.get("titular")),
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": {},
            "projetos": [],
            "_alterado": alterado,
        }
    lista = [{k: v for k, v in x.items() if k != "_alterado"} for x in por_pessoa.values()]
    return sorted(lista, key=lambda v: v["nome"])


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    entidade = entidade_de(url)
    if entidade is None:
        raise ValueError(f"Endereço fora do padrão da CR2: {url}")
    palavra = entidade.rsplit("-", 1)[-1]
    registros: list[dict] = []
    with comum.criar_cliente() as client:
        cursor = 0
        while True:
            time.sleep(PAUSA)
            resposta = comum.get_json(
                client,
                API,
                params={
                    "constraints": json.dumps(
                        [{"key": "Slug", "constraint_type": "text contains", "value": palavra}]
                    ),
                    "limit": 100,
                    "cursor": cursor,
                },
            )["response"]
            registros += resposta["results"]
            if not resposta["remaining"]:
                break
            cursor += len(resposta["results"])
    return {
        "base": PORTAL.format(entidade=entidade),
        "legislatura": None,
        "vereadores": vereadores(registros, entidade),
    }


def executar(limite: int | None = None) -> int:
    camaras = [
        (c["municipio_ibge"], c["url"])
        for c in catalogo.ler()
        if c["tipo"] == "sistema_legislativo" and c["sistema"] == SISTEMA
    ]
    camaras = camaras[:limite] if limite else camaras
    total, falhas = 0, 0
    for ibge, url in camaras:
        try:
            camara = coletar(url)
            if not camara["vereadores"]:
                raise ValueError("lista de vereadores vazia")
            with SessionLocal() as session:
                total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {url}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="API de dados abertos da CR2 (portalcr2.com.br/api/1.1/obj/parlamentares)",
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
