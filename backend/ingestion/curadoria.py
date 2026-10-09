"""Curadoria versionada: casos montados com documentos oficiais (data/casos/<slug>/) e
processos consultados à mão onde a fonte bloqueia acesso automático
(data/curadoria/processos.csv, ex.: STF e STJ).

Cada linha liga uma pessoa que já temos (pelo registro de origem, ex.:
"parlamentar:camara:204534") a um documento oficial, com o papel que o documento lhe dá.
A carga confere tudo e reprova se algo não bater (pessoa inexistente ou ligada só pelo
nome, nome de conferência diferente, papel desconhecido, link sem https, número de
processo com dígito verificador errado). Rascunhos (rascunho = true) nunca são
publicados. Revisão por pull request, como o catálogo de canais.

Formato em data/casos/README.md.
"""

import csv
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import Caso, CasoDocumento, Evento, FonteIngestao, Pessoa, PessoaVinculo
from app.models.pessoa import REGRAS_FORTES
from ingestion.identidade import casar_nome
from ingestion.normalizar import numero_cnj

FONTE = "curadoria"
DADOS = BACKEND_DIR.parent / "data"
PAPEIS = {
    "investigado": "investigado(a)",
    "indiciado": "indiciado(a)",
    "denunciado": "denunciado(a)",
    "reu": "réu/ré",
    "condenado": "condenado(a)",
    "absolvido": "absolvido(a)",
    "arquivado": "investigação arquivada",
    "extinta_punibilidade": "punibilidade extinta",
    "colaborador": "colaborador(a) em acordo homologado",
    "citado_colaboracao": "citado(a) em colaboração premiada homologada",
    "autor": "autor(a)",
}
TIPOS_DOCUMENTO = {"processo", "denuncia", "acordao", "sentenca", "decisao", "relatorio_cpi",
                   "sancao", "colaboracao"}  # fmt: skip


class CuradoriaInvalida(Exception):
    pass


@dataclass
class Resultado:
    erros: list[str] = field(default_factory=list)
    rascunhos: int = 0
    eventos: int = 0


def _ler_csv(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k.strip(): (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
        ]


def _data(valor: str) -> date | None:
    return date.fromisoformat(valor) if valor else None


def _sim(valor: str | bool | None) -> bool:
    return valor is True or str(valor).strip().lower() in {"true", "sim", "1"}


def resolver_pessoa(
    session: Session, referencia: str, nome_conferencia: str, onde: str, erros: list[str]
) -> int | None:
    """'parlamentar:camara:204534' -> id da pessoa, só se o vínculo for publicável e o
    nome de conferência casar com o nome da pessoa."""
    fonte, _, id_externo = referencia.partition(":")
    linha = session.execute(
        select(PessoaVinculo.pessoa_id, PessoaVinculo.regra, PessoaVinculo.revisado).where(
            PessoaVinculo.fonte == fonte, PessoaVinculo.id_externo == id_externo
        )
    ).first()
    if linha is None:
        erros.append(f"{onde}: pessoa {referencia!r} não encontrada")
        return None
    if linha.regra not in REGRAS_FORTES and not linha.revisado:
        erros.append(f"{onde}: {referencia!r} está ligada só pelo nome (revise o vínculo antes)")
        return None
    nome = session.scalar(select(Pessoa.nome).where(Pessoa.id == linha.pessoa_id))
    if casar_nome([nome_conferencia], [(1, nome)]) != 1:
        erros.append(f"{onde}: nome de conferência {nome_conferencia!r} não confere com {nome!r}")
        return None
    return linha.pessoa_id


def _vinculo(session: Session, pessoa_id: int, id_externo: str) -> int:
    return session.scalar(
        insert(PessoaVinculo)
        .values(
            pessoa_id=pessoa_id, fonte=FONTE, id_externo=id_externo, regra="curadoria",
            revisado=True,
        )
        .returning(PessoaVinculo.id)
    )  # fmt: skip


def carregar_caso(session: Session, pasta: Path, resultado: Resultado, ingestao_id: int | None):
    with (pasta / "caso.toml").open("rb") as arquivo:
        meta = tomllib.load(arquivo)
    if _sim(meta.get("rascunho")):
        resultado.rascunhos += 1
        return
    slug = pasta.name
    erros = resultado.erros
    for campo in ("nome", "resumo", "conferido_em"):
        if not meta.get(campo):
            erros.append(f"{slug}/caso.toml: falta {campo}")
    documentos = {}
    for i, d in enumerate(_ler_csv(pasta / "documentos.csv"), start=2):
        onde = f"{slug}/documentos.csv:{i}"
        if d.get("tipo") not in TIPOS_DOCUMENTO:
            erros.append(f"{onde}: tipo {d.get('tipo')!r} desconhecido")
        if not d.get("url", "").startswith("https://"):
            erros.append(f"{onde}: link precisa ser https e oficial")
        if d.get("numero_cnj") and not numero_cnj(d["numero_cnj"]):
            erros.append(f"{onde}: número CNJ inválido {d['numero_cnj']!r}")
        documentos[d.get("codigo")] = d
    participacoes = []
    for i, p in enumerate(_ler_csv(pasta / "pessoas.csv"), start=2):
        onde = f"{slug}/pessoas.csv:{i}"
        if p.get("papel") not in PAPEIS:
            erros.append(f"{onde}: papel {p.get('papel')!r} desconhecido")
        if p.get("documento") not in documentos:
            erros.append(f"{onde}: documento {p.get('documento')!r} não está em documentos.csv")
        if not p.get("descricao"):
            erros.append(f"{onde}: falta a descrição factual")
        pessoa_id = resolver_pessoa(session, p.get("pessoa", ""), p.get("nome_conferencia", ""),
                                    onde, erros)  # fmt: skip
        participacoes.append((p, pessoa_id))
    if erros:
        return
    session.execute(delete(Caso).where(Caso.slug == slug))  # documentos e eventos em cascata
    session.add(
        Caso(slug=slug, nome=meta["nome"], periodo=meta.get("periodo"), resumo=meta["resumo"],
             conferido_em=_data(str(meta["conferido_em"])))
    )  # fmt: skip
    session.flush()
    for d in documentos.values():
        session.add(
            CasoDocumento(caso_slug=slug, codigo=d["codigo"], tipo=d["tipo"], orgao=d["orgao"],
                          numero=numero_cnj(d.get("numero_cnj")) or d.get("numero") or None,
                          data=_data(d.get("data", "")), url=d["url"], resumo=d["resumo"])
        )  # fmt: skip
    for p, pessoa_id in participacoes:
        documento = documentos[p["documento"]]
        id_externo = f"caso:{slug}:{p['documento']}:{p['pessoa']}"
        session.add(
            Evento(
                pessoa_id=pessoa_id, vinculo_id=_vinculo(session, pessoa_id, id_externo),
                data=_data(p.get("data", "")) or _data(documento.get("data", "")),
                tipo="caso", descricao=p["descricao"], orgao=documento["orgao"][:120],
                numero_processo=numero_cnj(documento.get("numero_cnj")),
                situacao=PAPEIS[p["papel"]], fonte=FONTE, id_externo=id_externo,
                fonte_url=documento["url"], ingestao_id=ingestao_id, caso_slug=slug,
            )
        )  # fmt: skip
        resultado.eventos += 1


def carregar_processos(session: Session, caminho: Path, resultado: Resultado, ingestao_id):
    """Processos consultados à mão (STF, STJ). Um evento por pessoa e processo."""
    erros = resultado.erros
    for i, p in enumerate(_ler_csv(caminho), start=2):
        onde = f"{caminho.name}:{i}"
        if _sim(p.get("rascunho")):
            resultado.rascunhos += 1
            continue
        obrigatorios = ("tribunal", "classe", "numero", "papel", "url", "conferido_em",
                        "conferido_por")  # fmt: skip
        faltam = [c for c in obrigatorios if not p.get(c)]
        if faltam:
            erros.append(f"{onde}: faltam {', '.join(faltam)}")
            continue
        if p["papel"] not in PAPEIS:
            erros.append(f"{onde}: papel {p['papel']!r} desconhecido")
        if not p["url"].startswith("https://"):
            erros.append(f"{onde}: link precisa ser https e oficial")
        if p.get("numero_cnj") and not numero_cnj(p["numero_cnj"]):
            erros.append(f"{onde}: número CNJ inválido {p['numero_cnj']!r}")
        pessoa_id = resolver_pessoa(session, p.get("pessoa", ""), p.get("nome_conferencia", ""),
                                    onde, erros)  # fmt: skip
        if erros:
            continue
        relator = f", relator(a) {p['relator']}" if p.get("relator") else ""
        autuado = (
            f", autuado em {_data(p['data_autuacao']):%d/%m/%Y}" if p.get("data_autuacao") else ""
        )
        descricao = (
            f"Parte como {PAPEIS[p['papel']]} no processo {p['classe']} {p['numero']} no "
            f"{p['tribunal']}{relator}{autuado}."
        )
        id_externo = f"processo:{p['tribunal']}:{p['classe']}:{p['numero']}:{p['pessoa']}"
        situacao = p.get("situacao") or None
        if situacao:
            situacao = f"{situacao} (conferido em {_data(p['conferido_em']):%d/%m/%Y})"
        session.add(
            Evento(
                pessoa_id=pessoa_id, vinculo_id=_vinculo(session, pessoa_id, id_externo),
                data=_data(p.get("data_autuacao", "")), tipo="processo", descricao=descricao,
                orgao=p["tribunal"][:120],
                numero_processo=(
                    numero_cnj(p.get("numero_cnj")) or f"{p['classe']} {p['numero']}"[:40]
                ),
                situacao=situacao, fonte=FONTE, id_externo=id_externo, fonte_url=p["url"],
                ingestao_id=ingestao_id,
            )
        )  # fmt: skip
        resultado.eventos += 1


def processar(session: Session, dados: Path = DADOS, ingestao_id: int | None = None) -> Resultado:
    """Recria tudo o que veio da curadoria. Qualquer erro reprova a carga inteira."""
    session.execute(delete(PessoaVinculo).where(PessoaVinculo.fonte == FONTE))
    session.execute(delete(Caso))
    resultado = Resultado()
    pasta_casos = dados / "casos"
    for pasta in sorted(p for p in pasta_casos.glob("*") if (p / "caso.toml").exists()):
        carregar_caso(session, pasta, resultado, ingestao_id)
    carregar_processos(session, dados / "curadoria" / "processos.csv", resultado, ingestao_id)
    if resultado.erros:
        raise CuradoriaInvalida("\n".join(resultado.erros))
    return resultado


def executar() -> int:
    with SessionLocal() as session:
        ingestao = FonteIngestao(
            fonte=FONTE, url="data/casos e data/curadoria", arquivo_raw="(git)"
        )
        session.add(ingestao)
        session.flush()
        resultado = processar(session, ingestao_id=ingestao.id)
        ingestao.registros = resultado.eventos
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now(UTC)
        session.commit()
    print(f"{resultado.eventos} participações publicadas; {resultado.rascunhos} rascunhos")
    return resultado.eventos


if __name__ == "__main__":
    executar()
