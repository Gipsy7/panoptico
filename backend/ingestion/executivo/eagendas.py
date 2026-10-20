"""Agenda pública de agentes federais (e-Agendas, CGU), só das pessoas da base.

Arquivo aberto, sem token: `dados_e-agendas.zip` (~205 MB, um CSV UTF-8 por mês desde 10/2022,
~1,3 milhão de linhas, atualizado mensalmente). Uma linha por registro x agente público; um
mesmo registro (ID) se repete para cada agente que o declarou. Tipos: Reunião, Evento,
Audiência, Audiência pública, Viagem, Presentes e hospitalidades e Afastamento (este último
não entra: é só "fulano substitui sicrano").

O CPF vem mascarado (`***.827.438-**`) apenas dentro da coluna `Participantes`, nunca numa
coluna própria. Por isso a ligação à `pessoa` tem duas passadas: na primeira, cada
"NOME (CPF: ***.AAA.BBB-**)" cujos 6 dígitos do meio + nome batem com uma única pessoa da base
(regra forte `cpf_parcial_nome`, a mesma do cadastro de servidores) liga o nome àquela pessoa;
na segunda, as linhas cujo agente é um desses nomes são gravadas (assim viagens e presentes,
que não trazem participantes, também entram). O presidente não consta: a agenda dele não está
no e-Agendas. Entram ministros e outros agentes que foram candidatos.

Coleta mínima (LGPD): sem CPF em lugar nenhum; agentes públicos participantes só com nome,
cargo e órgão (e apenas os que a fonte publica com CPF mascarado); participantes privados só
pela entidade que representam ("... representando FENATRAD" vira "FENATRAD"), nunca o nome da
pessoa física; ofertante de hospitalidade com CPF vira "pessoa física". Recarga integral a
cada arquivo (o histórico inteiro vem no zip). Rode depois de ingestion.pessoas.
"""

import argparse
import csv
import html
import io
import re
import zipfile
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import AgendaCompromisso, FonteIngestao, Pessoa, PessoaVinculo
from ingestion import comum

FONTE = "eagendas"
URL = "https://dadosabertos-download.cgu.gov.br/dados_e-agendas/dados_e-agendas.zip"
PAGINA = "https://eagendas.cgu.gov.br/"
TIPOS = {
    "Reunião": "reuniao",
    "Evento": "evento",
    "Audiência": "audiencia",
    "Audiência pública": "audiencia_publica",
    "Viagem": "viagem",
    "Presentes e hospitalidades": "presente",
}
AGENTE = re.compile(
    r"^(?P<nome>.+?) \(CPF: \*\*\*\.(?P<a>\d{3})\.(?P<b>\d{3})-\*\*\)"
    r"(?: / (?P<cargo>.*?))?(?: / (?P<orgao>.*))?$"
)
CPF_EM_TEXTO = re.compile(r"\(CPF: [\d.*\-]+\)")
OFERTANTE_CPF = re.compile(r"Ofertante: [^:]*?\(CPF: [\d.*\-]+\)")
LOTE = 2000
MAX_PARTICIPANTES = 40
ROTULO_PUBLICOS = "Agentes públicos participantes:"
ROTULO_PRIVADOS = "Agentes privados participantes:"


def _texto(valor: str | None, limite: int | None = None) -> str | None:
    valor = (valor or "").strip()
    if valor in ("", "ND"):
        return None
    return valor[:limite] if limite else valor


def _data(valor: str | None) -> date | None:
    try:
        return datetime.strptime((valor or "").strip()[:10], "%d-%m-%Y").date()
    except ValueError:
        return None


def _hora(valor: str | None) -> time | None:
    try:
        return datetime.strptime((valor or "").strip(), "%H:%M").time()
    except ValueError:
        return None


def ler_linhas(arquivo: Path | bytes):
    """Linhas de todos os CSVs mensais do zip, em fluxo."""
    csv.field_size_limit(10**8)
    origem = io.BytesIO(arquivo) if isinstance(arquivo, bytes) else arquivo
    with zipfile.ZipFile(origem) as z:
        for nome in sorted(n for n in z.namelist() if n.endswith(".csv")):
            with z.open(nome) as bruto:
                yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8", newline=""))


def _itens_publicos(participantes: str) -> list[str]:
    secao = participantes.split(" || ")[0]
    if not secao.startswith(ROTULO_PUBLICOS):
        return []
    return [i.strip() for i in secao.split(":", 1)[1].split(" | ") if i.strip()]


def agentes_com_cpf(participantes: str) -> list[dict[str, str]]:
    """Agentes públicos da coluna Participantes que a fonte publica com CPF mascarado:
    nome, 6 dígitos do meio (só para ligar, nunca gravados), cargo e órgão."""
    achados = []
    for item in _itens_publicos(participantes):
        m = AGENTE.match(item)
        if m:
            achados.append(
                {
                    "nome": m["nome"].strip(),
                    "meio": m["a"] + m["b"],
                    "cargo": (m["cargo"] or "").strip(),
                    "orgao": (m["orgao"] or "").strip(),
                }
            )
    return achados


def entidades_privadas(participantes: str) -> tuple[list[str], int]:
    """(entidades representadas, número de participantes privados). O nome da pessoa física
    nunca é guardado; sem "representando" só entra na contagem."""
    privados = next(
        (s.split(":", 1)[1] for s in participantes.split(" || ") if s.startswith(ROTULO_PRIVADOS)),
        "",
    )
    itens = [i.strip() for i in privados.split(" | ") if i.strip()]
    entidades: list[str] = []
    for item in itens:
        if "representando" not in item.lower():
            continue
        entidade = re.split(r"representando", item, flags=re.IGNORECASE)[-1].strip(" -–:")
        # "Presidente - Chevron Brasil": o cargo vem antes; a entidade é o último trecho.
        ultimo = entidade.rsplit(" - ", 1)[-1].strip()
        entidade = ultimo if len(ultimo) >= 3 else entidade
        if entidade and entidade not in entidades:
            entidades.append(entidade[:100])
    return entidades[:MAX_PARTICIPANTES], len(itens)


def limpar_detalhes(detalhes: str) -> str | None:
    """Detalhes de viagem/presente sem CPF: ofertante pessoa física vira "pessoa física"."""
    texto = html.unescape(detalhes or "").strip()
    if texto in ("", "ND"):
        return None
    texto = OFERTANTE_CPF.sub("Ofertante: pessoa física", texto)
    return CPF_EM_TEXTO.sub("", texto).strip()[:2000]


def mapa_ligacao(linhas, indice: dict[tuple[str, str], set[int]]) -> dict[str, int]:
    """1ª passada: chave do nome -> pessoa, para os agentes cujo CPF parcial + nome batem com
    uma única pessoa. Nome ligado a pessoas diferentes é descartado."""
    ligados: dict[str, int] = {}
    ambiguos: set[str] = set()
    for linha in linhas:
        participantes = linha.get("Participantes") or ""
        if "(CPF:" not in participantes:
            continue
        for agente in agentes_com_cpf(participantes):
            chave = comum.chave_nome(agente["nome"])
            candidatos = indice.get((agente["meio"], chave), set())
            if len(candidatos) != 1:
                continue
            pessoa = next(iter(candidatos))
            if ligados.setdefault(chave, pessoa) != pessoa:
                ambiguos.add(chave)
    for chave in ambiguos:
        ligados.pop(chave, None)
    return ligados


def normalizar(linhas, ligados: dict[str, int]) -> list[dict[str, Any]]:
    """2ª passada: registros dos agentes ligados (um por pessoa, tipo e ID de registro)."""
    registros: dict[tuple[int, str, int], dict[str, Any]] = {}
    for linha in linhas:
        tipo = TIPOS.get(linha.get("Tipo de registro", ""))
        if tipo is None:
            continue
        pessoa = ligados.get(comum.chave_nome(linha.get("Nome")))
        if pessoa is None:
            continue
        try:
            id_registro = int(linha["ID do registro"])
        except (KeyError, ValueError):
            continue
        participantes = linha.get("Participantes") or ""
        publicos = agentes_com_cpf(participantes)
        entidades, n_privados = entidades_privadas(participantes)
        registros[(pessoa, tipo, id_registro)] = {
            "pessoa_id": pessoa,
            "tipo": tipo,
            "id_registro": id_registro,
            "cargo": _texto(linha.get("Cargo/Função"), 200),
            "orgao": _texto(linha.get("Órgão/Entidade"), 200),
            "data_inicio": _data(linha.get("Data de início")),
            "data_fim": _data(linha.get("Data de término")),
            "hora_inicio": _hora(linha.get("Hora de início")),
            "hora_fim": _hora(linha.get("Hora de término")),
            "forma": _texto(linha.get("Forma de realização"), 20),
            "assunto": _texto(
                linha.get("Vinculações")
                if tipo == "presente"
                else linha.get("Assunto do Compromisso")
            ),
            "local": _texto(linha.get("Local"), 200),
            "origem": _texto(linha.get("Origem"), 120),
            "destino": _texto(linha.get("Destino"), 120),
            "detalhes": (
                limpar_detalhes(linha.get("Detalhes") or "")
                if tipo in ("viagem", "presente")
                else None
            ),
            # Só os que a fonte publica com CPF mascarado têm nome guardado; os demais
            # (sem CPF, texto livre) aparecem só na contagem.
            "participantes_publicos": [
                {"nome": a["nome"], "cargo": a["cargo"], "orgao": a["orgao"]}
                for a in publicos[:MAX_PARTICIPANTES]
            ]
            or None,
            "n_participantes_publicos": len(_itens_publicos(participantes)),
            "entidades_privadas": entidades or None,
            "n_participantes_privados": n_privados,
            "publicado_em": _data(linha.get("Data da publicação")),
        }
    return list(registros.values())


def indice_pessoas(pessoas) -> dict[tuple[str, str], set[int]]:
    indice: dict[tuple[str, str], set[int]] = {}
    for id_, cpf, chave in pessoas:
        if cpf and chave:
            indice.setdefault((cpf[3:9], chave), set()).add(id_)
    return indice


def gravar(session: Session, registros: list[dict[str, Any]], ingestao_id: int | None) -> int:
    """Recarga integral: o zip traz o histórico completo e a CGU corrige registros antigos."""
    session.execute(delete(AgendaCompromisso))
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))
    for pessoa in sorted({r["pessoa_id"] for r in registros}):
        session.execute(
            insert(PessoaVinculo).values(
                pessoa_id=pessoa, fonte=FONTE, id_externo=f"pessoa:{pessoa}",
                regra="cpf_parcial_nome",
            )
        )  # fmt: skip
    for i in range(0, len(registros), LOTE):
        session.execute(
            insert(AgendaCompromisso),
            [{**r, "ingestao_id": ingestao_id} for r in registros[i : i + LOTE]],
        )
    return len(registros)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL)

    def carregar(session: Session, payload: Path | bytes, ingestao: FonteIngestao) -> int:
        pessoas = session.execute(select(Pessoa.id, Pessoa.cpf, Pessoa.chave_nome)).all()
        ligados = mapa_ligacao(ler_linhas(payload), indice_pessoas(pessoas))
        linhas = comum.ContaLinhas(ler_linhas(payload))
        registros = normalizar(linhas, ligados)
        if linhas.total == 0:
            raise RuntimeError("e-Agendas vazio: nada alterado.")
        comum.conferir_carga(ingestao, registros, total_fonte=linhas.total)
        gravar(session, registros, ingestao.id)
        print(
            f"  {linhas.total} linhas no e-Agendas; {len(ligados)} agentes ligados a pessoas da"
            f" base; {len(registros)} registros gravados"
        )
        return len(registros)

    return comum.executar_ingestao(
        FONTE, URL, baixar, carregar, de_raw=de_raw,
        incremental=comum.Incremental(sonda=URL, contexto=comum.contexto_pessoas),
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um ZIP já baixado")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.de_raw)} registros de agenda ligados")
