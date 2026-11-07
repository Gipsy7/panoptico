"""O Plenário agora: sessão em andamento ou próxima sessão, da Câmara e do Senado.

Consulta direto as APIs oficiais (sem tabela, sem ingestão): a Câmara em `/eventos` do Plenário
(situação "Em Andamento") e o Senado na agenda do Plenário (`/plenario/agenda/mes/{data}`).
O resultado fica em cache por 3 minutos e, se a fonte falhar, vale a última resposta boa (com a
hora dela); sem nenhuma, a Casa aparece "sem sessão" e `indisponivel`. O Panóptico só aponta o
vídeo oficial (TV Câmara, TV Senado); não incorpora nem guarda vídeo.
"""

import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import httpx

# Brasília não tem horário de verão desde 2019; evita depender de tzdata no Windows.
BRASILIA = timezone(timedelta(hours=-3))
TTL_SEGUNDOS = 180
JANELA_DIAS = 14
MAX_ITENS = 8
USER_AGENT = "Panoptico/0.1 (+https://panoptico.social.br; contato@panoptico.social.br)"

FONTE_NOME = "Dados Abertos da Câmara e do Senado (Plenário)"
FONTE_URL = "https://dadosabertos.camara.leg.br/"

URL_CAMARA_EVENTOS = "https://dadosabertos.camara.leg.br/api/v2/eventos"
URL_CAMARA_PAUTA = "https://dadosabertos.camara.leg.br/api/v2/eventos/{id}/pauta"
URL_CAMARA_EVENTO = "https://www.camara.leg.br/evento-legislativo/{id}"
URL_SENADO_AGENDA = "https://legis.senado.leg.br/dadosabertos/plenario/agenda/mes/{data}"
URL_TV_SENADO = "https://www12.senado.leg.br/tv/plenario-e-comissoes/plenario"
ID_PLENARIO_CAMARA = 180

_SITUACOES_SENADO_AGORA = ("andamento", "aberta", "iniciada", "em curso")
_SITUACOES_SENADO_FIM = ("encerrad", "cancelad", "não realizada", "nao realizada", "suspens")

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_travas = {"camara": threading.Lock(), "senado": threading.Lock()}


def _cliente() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(6.0, connect=4.0),
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        follow_redirects=True,
        # Só IPv4, como a ingestão: a resolução com AAAA primeiro falha em algumas redes.
        transport=httpx.HTTPTransport(local_address="0.0.0.0"),
    )


def _limpar(texto: str | None) -> str:
    return " ".join((texto or "").split())


def _resumo(texto: str | None, limite: int = 220) -> str:
    texto = _limpar(texto)
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def _lista(valor: Any) -> list[dict[str, Any]]:
    """O Senado devolve objeto quando há um item só."""
    if not valor:
        return []
    return valor if isinstance(valor, list) else [valor]


def _quando(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto).replace(tzinfo=BRASILIA)
    except ValueError:
        return None


def _local(momento: datetime) -> str:
    return momento.replace(tzinfo=None).isoformat(timespec="minutes")


def _vazio(casa: str, situacao: str = "sem", *, indisponivel: bool = False) -> dict[str, Any]:
    return {
        "casa": casa,
        "situacao": situacao,
        "titulo": None,
        "inicio": None,
        "itens": [],
        "total_itens": 0,
        "url_video": None,
        "rotulo_video": "TV Câmara" if casa == "camara" else "TV Senado",
        "proxima": None,
        "indisponivel": indisponivel,
    }


# ---------------------------------------------------------------- Câmara


def _itens_camara(pauta: list[dict[str, Any]]) -> tuple[list[dict[str, str]], int]:
    vistos: set[tuple[Any, str]] = set()
    itens: list[dict[str, str]] = []
    for item in sorted(pauta, key=lambda i: i.get("ordem") or 0):
        materia = item.get("proposicaoRelacionada_") or item.get("proposicao_") or {}
        rotulo = _limpar(item.get("titulo"))
        if not rotulo and materia.get("siglaTipo") and materia.get("numero"):
            rotulo = f"{materia['siglaTipo']} {materia['numero']}/{materia.get('ano')}"
        chave = (item.get("ordem"), rotulo)
        if not rotulo or chave in vistos:
            continue
        vistos.add(chave)
        itens.append({"rotulo": rotulo, "descricao": _resumo(materia.get("ementa"))})
    return itens[:MAX_ITENS], len(itens)


def consultar_camara(client: httpx.Client, agora: datetime) -> dict[str, Any]:
    resp = client.get(
        URL_CAMARA_EVENTOS,
        params={
            "idOrgao": ID_PLENARIO_CAMARA,
            "dataInicio": (agora.date() - timedelta(days=1)).isoformat(),
            "dataFim": (agora.date() + timedelta(days=JANELA_DIAS)).isoformat(),
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "dataHoraInicio",
        },
    )
    resp.raise_for_status()
    eventos = [
        e
        for e in resp.json().get("dados", [])
        if (e.get("descricaoTipo") or "").startswith("Sessão")
    ]
    em_andamento = [
        e for e in eventos if (e.get("situacao") or "").lower().startswith("em andamento")
    ]
    if em_andamento:
        evento = em_andamento[0]
        r = _vazio("camara", "agora")
        pauta_resp = client.get(URL_CAMARA_PAUTA.format(id=evento["id"]))
        if pauta_resp.status_code != 404:
            pauta_resp.raise_for_status()
            r["itens"], r["total_itens"] = _itens_camara(pauta_resp.json().get("dados", []))
        r.update(
            titulo=_limpar(evento.get("descricaoTipo")),
            inicio=evento.get("dataHoraInicio"),
            url_video=evento.get("urlRegistro") or URL_CAMARA_EVENTO.format(id=evento["id"]),
        )
        return r
    for evento in eventos:
        inicio = _quando(evento.get("dataHoraInicio"))
        situacao = (evento.get("situacao") or "").lower()
        if inicio and inicio > agora and not situacao.startswith(("cancelad", "encerrad")):
            r = _vazio("camara", "proxima")
            r["proxima"] = {
                "inicio": evento["dataHoraInicio"],
                "titulo": _limpar(evento.get("descricaoTipo")),
            }
            return r
    return _vazio("camara")


# ---------------------------------------------------------------- Senado


def _inicio_senado(sessao: dict[str, Any]) -> datetime | None:
    return _quando(f"{sessao.get('Data', '')}T{sessao.get('Hora') or '00:00'}")


def _itens_senado(sessao: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    itens = []
    for materia in _lista((sessao.get("Materias") or {}).get("Materia")):
        rotulo = _limpar(materia.get("DescricaoIdentificacaoMateria"))
        if rotulo:
            ementa = materia.get("EmentaPapeleta") or materia.get("Ementa")
            itens.append({"rotulo": rotulo, "descricao": _resumo(ementa)})
    return itens[:MAX_ITENS], len(itens)


def _sessoes_senado(client: httpx.Client, hoje: date) -> list[dict[str, Any]]:
    consultas = [hoje]
    fim = hoje + timedelta(days=JANELA_DIAS)
    if (fim.year, fim.month) != (hoje.year, hoje.month):
        consultas.append(fim.replace(day=1))
    sessoes: list[dict[str, Any]] = []
    for data in consultas:
        resp = client.get(URL_SENADO_AGENDA.format(data=f"{data:%Y%m%d}"))
        resp.raise_for_status()
        agenda = resp.json().get("AgendaPlenario") or {}
        sessoes += _lista((agenda.get("Sessoes") or {}).get("Sessao"))
    return sessoes


def consultar_senado(client: httpx.Client, agora: datetime) -> dict[str, Any]:
    sessoes = _sessoes_senado(client, agora.date())
    for sessao in sessoes:
        situacao = _limpar(sessao.get("SituacaoSessao")).lower()
        if any(t in situacao for t in _SITUACOES_SENADO_AGORA):
            r = _vazio("senado", "agora")
            r["itens"], r["total_itens"] = _itens_senado(sessao)
            inicio = _inicio_senado(sessao)
            r.update(
                titulo=_limpar(sessao.get("TipoSessao")).capitalize(),
                inicio=_local(inicio) if inicio else None,
                url_video=URL_TV_SENADO,
            )
            return r
    futuras = []
    for sessao in sessoes:
        situacao = _limpar(sessao.get("SituacaoSessao")).lower()
        inicio = _inicio_senado(sessao)
        if inicio and inicio > agora and not any(t in situacao for t in _SITUACOES_SENADO_FIM):
            futuras.append((inicio, sessao))
    if futuras:
        inicio, sessao = min(futuras, key=lambda p: p[0])
        r = _vazio("senado", "proxima")
        r["proxima"] = {
            "inicio": _local(inicio),
            "titulo": _limpar(sessao.get("TipoSessao")).capitalize(),
        }
        return r
    return _vazio("senado")


# ---------------------------------------------------------------- Conjunto

_CONSULTAS = {"camara": consultar_camara, "senado": consultar_senado}


def _da_casa(casa: str, fabrica: Callable[[], httpx.Client], agora: datetime) -> dict[str, Any]:
    with _travas[casa]:
        guardado = _cache.get(casa)
        if guardado and time.monotonic() - guardado[0] < TTL_SEGUNDOS:
            return guardado[1]
        try:
            with fabrica() as client:
                dados = _CONSULTAS[casa](client, agora)
            dados["conferido_em"] = agora.astimezone(UTC).isoformat(timespec="seconds")
            _cache[casa] = (time.monotonic(), dados)
            return dados
        except (httpx.HTTPError, ValueError, KeyError):
            if guardado:  # a última resposta boa, com a hora dela
                return guardado[1]
            dados = _vazio(casa, indisponivel=True)
            dados["conferido_em"] = None
            return dados


def ao_vivo(
    fabrica: Callable[[], httpx.Client] = _cliente, agora: datetime | None = None
) -> dict[str, Any]:
    agora = agora or datetime.now(BRASILIA)
    casas = [_da_casa(casa, fabrica, agora) for casa in ("camara", "senado")]
    conferidos = [c["conferido_em"] for c in casas if c["conferido_em"]]
    return {
        "conferido_em": min(conferidos) if conferidos else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "casas": casas,
    }


def limpar_cache() -> None:
    _cache.clear()
