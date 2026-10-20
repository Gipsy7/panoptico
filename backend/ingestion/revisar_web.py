"""Revisão humana pelo navegador: a mesma fila e os mesmos CSVs de `ingestion.revisar`, numa
página local com botões e atalhos de teclado (A aceita, R recusa, P pula, U desfaz).

Uso (com DATABASE_URL apontando para o acervo):
    python -m ingestion.revisar_web            # abre http://127.0.0.1:8765
    python -m ingestion.revisar_web --porta 9000 --sem-navegador

Só escuta em 127.0.0.1. Cada decisão é gravada na hora no CSV da fila (data/*_revisados.csv),
como no terminal; "desfazer" tira a última linha gravada nesta sessão.
"""

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Candidatura, Foto, MandatoLocal
from ingestion import revisar

TIPOS = {
    "vinculo": ("Vínculos por nome aproximado", revisar.pendentes, revisar.REVISOES),
    "cpi": ("Indiciamentos de CPI", revisar.pendentes_indiciamentos,
            revisar.INDICIAMENTOS_REVISADOS),
    "diario": ("Atos dos diários municipais", revisar.pendentes_atos, revisar.ATOS_REVISADOS),
    "dou": ("Atos do DOU", revisar.pendentes_dou, revisar.DOU_REVISADOS),
}  # fmt: skip

_filas: dict[str, list[dict]] = {}
_feitas: list[tuple[str, dict, bytes]] = []  # (tipo, item, registro gravado) p/ desfazer
_trava = threading.Lock()


def _sinais_do_vinculo(session, item: dict) -> dict:
    """O que ajuda a decidir sem sair da página: a foto que a casa publica, a foto do TSE
    (quando a carga de fotos já trouxe) e o partido de cada lado, com o ano da eleição."""
    casa, uf, ibge, id_externo = item["id_externo"].split(":", 3)
    mandato = session.scalar(
        select(MandatoLocal).where(
            MandatoLocal.casa == casa, MandatoLocal.uf == uf,
            MandatoLocal.id_externo == id_externo,
            (MandatoLocal.municipio_ibge == ibge) if ibge
            else MandatoLocal.municipio_ibge.is_(None),
        )
    )  # fmt: skip
    _, ano, sq = item["ligado_a"].split(":", 2)
    c = session.scalar(
        select(Candidatura).where(
            Candidatura.ano_eleicao == int(ano), Candidatura.sq_candidato == sq
        )
    )
    tem_foto = c is not None and session.scalar(
        select(Foto.candidatura_id).where(Foto.candidatura_id == c.id)
    )
    return {
        "foto_casa": (mandato.foto_url if mandato else None) or "",
        "foto_tse": f"/api/foto/{c.id}" if tem_foto else "",
        "partido_tse": (c.partido if c else None) or "",
        "ano_tse": ano,
    }


def _fila(tipo: str) -> list[dict]:
    if tipo not in _filas:
        with SessionLocal() as session:
            fila = TIPOS[tipo][1](session)
            if tipo == "vinculo":
                fila = [{**item, **_sinais_do_vinculo(session, item)} for item in fila]
            _filas[tipo] = fila
    return _filas[tipo]


def _registro_gravado(caminho: Path, inicio: int | None) -> bytes:
    """Os bytes que a gravação acrescentou ao CSV a partir de `inicio` (o tamanho antes; None
    se o arquivo não existia), sem o cabeçalho quando o arquivo foi criado agora. É o registro
    inteiro, mesmo quando a observação tem quebra de linha e ocupa mais de uma linha."""
    novo = caminho.read_bytes()[inicio or 0 :]
    if inicio is None:
        novo = novo.split(b"\n", 1)[1]  # o cabeçalho não tem quebra de linha dentro
    return novo


def decidir(tipo: str, indice: int, decisao: str, revisor: str, pessoa_chave: str = "",
            observacao: str = "") -> None:  # fmt: skip
    fila = _fila(tipo)
    item = fila[indice]
    caminho = TIPOS[tipo][2]
    inicio = caminho.stat().st_size if caminho.exists() else None
    if tipo == "cpi":
        revisar.gravar_indiciamento(item, decisao, revisor, pessoa_chave=pessoa_chave,
                                    observacao=observacao)  # fmt: skip
    else:
        gravar = {"vinculo": revisar.gravar_decisao, "diario": revisar.gravar_ato,
                  "dou": revisar.gravar_dou}[tipo]  # fmt: skip
        gravar(item, decisao, revisor, observacao)
    _feitas.append((tipo, item, _registro_gravado(caminho, inicio)))
    fila.pop(indice)


def desfazer() -> str | None:
    """Tira do CSV a última decisão desta sessão e devolve o item ao começo da fila."""
    if not _feitas:
        return None
    tipo, item, registro = _feitas[-1]
    caminho = TIPOS[tipo][2]
    conteudo = caminho.read_bytes()
    if not conteudo.endswith(registro):
        raise RuntimeError(f"{caminho.name} mudou fora desta página; desfaça à mão.")
    caminho.write_bytes(conteudo[: len(conteudo) - len(registro)])
    _feitas.pop()
    _fila(tipo).insert(0, item)
    return tipo


class Manipulador(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def _responder(self, corpo: bytes, tipo: str = "application/json", status: int = 200):
        self.send_response(status)
        texto = tipo.startswith(("text/", "application/json"))
        self.send_header("Content-Type", f"{tipo}; charset=utf-8" if texto else tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dado, status: int = 200) -> None:
        self._responder(json.dumps(dado, ensure_ascii=False).encode(), status=status)

    def do_GET(self) -> None:
        if self.path == "/":
            return self._responder(PAGINA.encode(), "text/html")
        if self.path == "/api/tipos":
            return self._json({t: r for t, (r, _, _) in TIPOS.items()})
        if self.path.startswith("/api/foto/"):
            with SessionLocal() as session:
                webp = session.scalar(
                    select(Foto.webp).where(Foto.candidatura_id == int(self.path.rsplit("/", 1)[1]))
                )
            if webp is None:
                return self._json({"erro": "sem foto"}, 404)
            return self._responder(webp, "image/webp")
        if self.path.startswith("/api/fila/"):
            tipo = self.path.rsplit("/", 1)[1]
            if tipo not in TIPOS:
                return self._json({"erro": "tipo desconhecido"}, 404)
            with _trava:
                fila = _fila(tipo)
                return self._json({"total": len(fila), "itens": fila[:50],
                                   "desfazer": bool(_feitas)})  # fmt: skip
        self._json({"erro": "não encontrado"}, 404)

    def do_POST(self) -> None:
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        try:
            with _trava:
                if self.path == "/api/decidir":
                    if corpo["decisao"] not in ("aceito", "recusado"):
                        raise ValueError("decisão inválida")
                    if not corpo.get("revisor", "").strip():
                        raise ValueError("preencha seu nome")
                    if _fila(corpo["tipo"])[int(corpo["indice"])] != corpo.get("item"):
                        raise ValueError("a fila mudou; recarregue a página")
                    decidir(corpo["tipo"], int(corpo["indice"]), corpo["decisao"],
                            corpo["revisor"].strip(), corpo.get("pessoa_chave", ""),
                            corpo.get("observacao", "").strip())  # fmt: skip
                    return self._json({"ok": True})
                if self.path == "/api/desfazer":
                    return self._json({"ok": True, "tipo": desfazer()})
        except (KeyError, IndexError, ValueError, RuntimeError) as erro:
            return self._json({"erro": str(erro)}, 400)
        self._json({"erro": "não encontrado"}, 404)


PAGINA = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revisão humana pelo navegador")
    parser.add_argument("--porta", type=int, default=8765)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args(argv)
    endereco = f"http://127.0.0.1:{args.porta}"
    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Manipulador)
    print(f"Revisão aberta em {endereco} (Ctrl+C para sair)", file=sys.stderr)
    if not args.sem_navegador:
        threading.Timer(1, webbrowser.open, [endereco]).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
