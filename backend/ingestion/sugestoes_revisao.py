"""Fila de revisão humana dos avisos de erro e das respostas de quem é citado (Frente 7).

Uso: python -m ingestion.revisar --tipo sugestao [--exportar fila.csv]

- Aviso de erro: [a]ceitar (conferido com a fonte oficial; em seguida, se o site mudou,
  registra a correção pública), [r]ecusar, [p]ular, [s]air.
- Resposta: p[u]blicar (só depois de confirmar a identidade pelo canal oficial: e-mail
  funcional da Casa ou ofício), [r]ecusar, [p]ular, [s]air. O texto só pode ser ajustado para
  tirar dados pessoais; o site não edita nem comenta.
- Ao fechar uma sugestão, o contato de quem mandou pode ser apagado na hora.
- --exportar grava a fila em CSV sem o contato.
"""

import csv
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.services import sugestoes as servico

CANAIS = {"email_funcional": "e-mail funcional da Casa", "oficio": "ofício"}


def exportar(destino: Path, session: Session | None = None) -> int:
    def _gravar(s: Session) -> int:
        fila = servico.pendentes(s)
        colunas = list(fila[0].keys()) if fila else ["id", "protocolo", "tipo", "texto"]
        with destino.open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=[*colunas, "decisao"])
            escritor.writeheader()
            escritor.writerows(fila)
        print(f"{len(fila)} sugestões em {destino} (sem o contato).", file=sys.stderr)
        return 0

    if session is not None:
        return _gravar(session)
    with SessionLocal() as s:
        return _gravar(s)


def _correcao(session: Session, item: dict, entrada: Callable[[str], str]) -> None:
    print("  Correção pública (aparece em /sobre-as-fontes#correcoes, sem quem avisou):")
    campos = {
        "dado": entrada("    O que foi corrigido (ex.: Gastos do gabinete em 2026): ").strip(),
        "antes": entrada("    Como estava: ").strip(),
        "depois": entrada("    Como ficou: ").strip(),
        "motivo": entrada("    Motivo: ").strip(),
        "fonte": entrada("    Fonte oficial conferida (link ou documento): ").strip(),
    }
    try:
        servico.registrar_correcao(session, **campos, sugestao_id=item["id"])
        print("  Correção registrada.")
    except ValueError as erro:
        print(f"  Correção não registrada: {erro}")


def _apagar_contato(session: Session, item: dict, entrada: Callable[[str], str]) -> None:
    if item["tem_contato"] != "sim":
        return
    if entrada("  Apagar o contato agora? [S/n]: ").strip().lower() != "n":
        servico.apagar_contato(session, item["id"])
        print("  Contato apagado.")


def _mostrar(session: Session, i: int, total: int, item: dict) -> None:
    rotulo = "AVISO DE ERRO" if item["tipo"] == "erro" else "RESPOSTA DE QUEM É CITADO"
    print(f"\n[{i}/{total}] {item['protocolo']}  {rotulo}  recebida em {item['criada_em']}")
    if item["categoria"]:
        print(f"  categoria: {item['categoria']}")
    perfil = f"{item['perfil_tipo']} {item['perfil_id']}".strip()
    if perfil:
        print(f"  perfil:    {perfil} {item['perfil_nome']}".rstrip())
    print(f"  página:    {item['pagina']}  {item['secao']}".rstrip())
    if item["confirmacao"]:
        print(f"  confirmar identidade por: {CANAIS.get(item['confirmacao'], item['confirmacao'])}")
    contato = servico.contato_de(session, item["id"])
    if contato:
        print(f"  contato:   {contato}")
    print(f"  texto:     {item['texto']}")


def revisar(session: Session | None = None, entrada: Callable[[str], str] = input) -> int:
    if session is None:
        with SessionLocal() as s:
            return revisar(s, entrada)
    fila = servico.pendentes(session)
    print(f"{len(fila)} avisos e respostas esperando revisão", file=sys.stderr)
    for i, item in enumerate(fila, start=1):
        _mostrar(session, i, len(fila), item)
        if item["tipo"] == "erro":
            pergunta = "  Conferido com a fonte? [a]ceitar, [r]ecusar, [p]ular, [s]air: "
        else:
            pergunta = "  p[u]blicar, [r]ecusar, [p]ular, [s]air: "
        resposta = entrada(pergunta).strip().lower()
        if resposta == "s":
            break
        if resposta == "r":
            servico.recusar(session, item["id"], entrada("  Nota (opcional): ").strip())
            _apagar_contato(session, item, entrada)
        elif resposta == "a" and item["tipo"] == "erro":
            servico.aceitar(session, item["id"], entrada("  Nota (opcional): ").strip())
            if (
                entrada("  O site mudou? Registrar correção pública? [s/N]: ").strip().lower()
                == "s"
            ):
                _correcao(session, item, entrada)
            _apagar_contato(session, item, entrada)
        elif resposta == "u" and item["tipo"] == "resposta":
            canal = CANAIS.get(item["confirmacao"], "canal oficial")
            confirmou = (
                entrada(f"  A identidade foi confirmada por {canal}? Digite 'confirmado': ")
                .strip()
                .lower()
                == "confirmado"
            )
            if not confirmou:
                print("  Não publicada: falta confirmar a identidade.")
                continue
            texto = entrada("  Texto sem dados pessoais (Enter mantém o original): ")
            servico.publicar_resposta(
                session, item["id"], identidade_confirmada=True, texto=texto or None,
                nota=entrada("  Nota (opcional): ").strip(),
            )  # fmt: skip
            print("  Publicada no perfil.")
            _apagar_contato(session, item, entrada)
    return 0
