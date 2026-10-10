"""Segunda varredura dos canais oficiais: só as cidades que a primeira não achou.

Testa variações de domínio que a primeira não testou (sem "de/do/da", `.leg.br` e
`.gov.br` com `cm`/`camara`/`camaramunicipal`, `.org.br` e `.com.br`, e o `sapl.` de cada
uma). Só aceita a página que responde 200 e se diz Câmara Municipal da cidade (nome da
cidade e "Câmara" no título ou no começo do texto), para não aceitar domínio parado ou de
outra cidade. Respeita o robots.txt, faz uma requisição por vez por servidor e poucas
cidades em paralelo.

    python -m ingestion.canais.segunda_varredura --ibge-raw <json do IBGE> [--limite N]
"""

import argparse
import asyncio
import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from ingestion.canais.varredura import CATALOGO, Pagina, Varredura, gravar_catalogo, slugs
from ingestion.comum import USER_AGENT, chave_nome

CURADOS = CATALOGO.with_name("canais_curados.csv")
SEM_CANAL = CATALOGO.with_name("cidades_sem_canal.csv")
PARTICULAS = {"de", "do", "da", "dos", "das", "e"}
PREFIXOS = ("camara", "cm", "camaramunicipal")
# Páginas de domínio parado ou à venda.
ESTACIONADO = re.compile(
    r"dom[ií]nio (est[aá] )?à venda|this domain|domain is for sale|"
    r"parked|dom[ií]nio estacionado|hospedagem de sites|registro\.br",
    re.I,
)


def _palavras(nome: str) -> list[str]:
    return [p for p in slugs(nome)[-1].split("-") if p]


def variacoes_slug(nome: str) -> list[str]:
    """'São Bento do Sul' -> saobentodosul, sao-bento-do-sul, saobentosul, sao-bento-sul."""
    palavras = _palavras(nome)
    sem = [p for p in palavras if p not in PARTICULAS] or palavras
    return list(dict.fromkeys(["".join(palavras), "-".join(palavras), "".join(sem), "-".join(sem)]))


def variacoes(nome: str, uf: str) -> list[str]:
    """Hosts de site da câmara que a primeira varredura não testou. A primeira já testou,
    com o nome inteiro (junto e com hífen): `{c}.{uf}.leg.br`, `camara{c}` e `cm{c}` em
    `.{uf}.gov.br`, com e sem www."""
    uf = uf.lower()
    ja = set()
    for s in slugs(nome):
        ja |= {f"{s}.{uf}.leg.br", f"camara{s}.{uf}.gov.br", f"cm{s}.{uf}.gov.br"}
    hosts: list[str] = []
    for s in variacoes_slug(nome):
        hosts.append(f"{s}.{uf}.leg.br")
        for p in PREFIXOS:
            hosts += [f"{p}{s}.{uf}.gov.br", f"{p}{s}.{uf}.leg.br"]
            hosts += [f"{p}{s}.org.br", f"{p}{s}.com.br"]
        hosts.append(f"camara.{s}.{uf}.gov.br")
    return [h for h in dict.fromkeys(hosts) if h not in ja]


def tem_uf_no_dominio(host: str, uf: str) -> bool:
    return f".{uf.lower()}." in host


def e_camara_da_cidade(pagina: Pagina, nome: str, uf: str, uf_nome: str, host: str) -> bool:
    """A página é da Câmara Municipal da cidade: o nome da cidade (palavras inteiras) e
    "câmara" no título ou no começo do texto, e nada de domínio parado."""
    inicio = pagina.texto[:20000]
    if ESTACIONADO.search(pagina.titulo) or (
        len(inicio.strip()) < 600 and ESTACIONADO.search(inicio)
    ):
        return False
    titulo = f" {chave_nome(pagina.titulo)} "
    texto = f" {chave_nome(inicio)} "
    cidade = f" {chave_nome(nome)} "
    if cidade not in titulo and not (cidade in texto and " CAMARA " in titulo):
        return False
    if " CAMARA " not in titulo and "CAMARA MUNICIPAL" not in texto:
        return False
    if not tem_uf_no_dominio(host, uf):
        # .com.br/.org.br não dizem o estado: a página tem de dizer, para não aceitar
        # uma cidade homônima de outro estado.
        if f" {chave_nome(uf_nome)} " not in texto and not re.search(rf"\b{uf}\b", inicio):
            return False
    return True


class Segunda(Varredura):
    def __init__(self, conexoes: int = 8, tempo: float = 8.0, pausa: float = 0.3) -> None:
        super().__init__(conexoes, tempo, pausa)
        self.robots: dict[str, RobotFileParser | None] = {}

    async def permitido(self, host: str, caminho: str = "/") -> bool:
        if host not in self.robots:
            resposta = await self._get(f"https://{host}/robots.txt")
            regras = None
            if (
                resposta is not None
                and resposta.status_code == 200
                and "html" not in resposta.headers.get("content-type", "")
            ):
                regras = RobotFileParser()
                regras.parse(resposta.text.splitlines())
            self.robots[host] = regras
        regras = self.robots[host]
        return regras is None or regras.can_fetch(USER_AGENT, caminho)

    async def sapl_da_cidade(self, host: str, nome: str, uf: str, uf_nome: str) -> str | None:
        """`sapl.{host}` com API aberta cuja página inicial é da câmara da cidade."""
        sapl = f"sapl.{host.removeprefix('www.')}"
        if not await self._servidor(f"https://{sapl}/") or not await self.permitido(sapl, "/api/"):
            return None
        if not await self.e_sapl(f"https://{sapl}/"):
            return None
        pagina = await self.pagina(f"https://{sapl}/")
        if pagina and e_camara_da_cidade(pagina, nome, uf, uf_nome, sapl):
            return f"https://{sapl}/"
        return None

    async def cidade_sem_canal(self, ibge: str, nome: str, uf: str, uf_nome: str) -> list[dict]:
        base = {
            "ibge": ibge,
            "municipio": nome,
            "uf": uf,
            "verificado_em": date.today().isoformat(),
        }
        hosts = variacoes(nome, uf)
        vivos = await asyncio.gather(*(self._servidor(f"https://{h}/") for h in hosts))
        vivos = [h for h, v in zip(hosts, vivos, strict=True) if v]
        for host in vivos:
            if not await self.permitido(host):
                continue
            pagina = await self.pagina(f"https://{host}/")
            if not pagina:
                continue
            final = urlparse(pagina.url).hostname or host
            if not final.endswith(".br") or not e_camara_da_cidade(
                pagina, nome, uf, uf_nome, final
            ):
                continue
            achados = [{**base, "tipo": "camara", "url": pagina.url, "sistema": ""}]
            if sapl := await self.sapl_da_cidade(final, nome, uf, uf_nome):
                achados.append({**base, "tipo": "sapl", "url": sapl, "sistema": "sapl"})
            return achados
        # Sem site nas variações, mas pode existir só o SAPL.
        for host in hosts:
            if sapl := await self.sapl_da_cidade(host, nome, uf, uf_nome):
                return [
                    {**base, "tipo": "camara", "url": sapl, "sistema": ""},
                    {**base, "tipo": "sapl", "url": sapl, "sistema": "sapl"},
                ]
        return []


def ler_ibge_raw(caminho: Path) -> list[tuple[str, str, str, str]]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return sorted(
        (str(m["municipio-id"]), m["municipio-nome"], m["UF-sigla"], m["UF-nome"]) for m in dados
    )


def sem_canal(municipios: list, catalogo: Path = CATALOGO, curados: Path = CURADOS) -> list:
    """As cidades que não aparecem no catálogo (nem nos curados) com nenhum canal."""
    com = set()
    for arquivo in (catalogo, curados):
        if arquivo.exists():
            with arquivo.open(encoding="utf-8", newline="") as f:
                com |= {linha["ibge"] for linha in csv.DictReader(f)}
    return [m for m in municipios if m[0] not in com]


async def varrer(municipios: list, conexoes: int = 8) -> list[dict]:
    varredura = Segunda()
    cidades = asyncio.Semaphore(conexoes)
    feitos = 0

    async def uma(m) -> list[dict]:
        nonlocal feitos
        async with cidades:
            try:
                return await varredura.cidade_sem_canal(*m)
            except Exception as erro:  # um site estranho não derruba a varredura
                print(f"  {m[1]}/{m[2]}: {erro.__class__.__name__}: {str(erro)[:100]}")
                return []
            finally:
                feitos += 1
                if feitos % 50 == 0:
                    print(f"  {feitos} de {len(municipios)} cidades", flush=True)

    try:
        resultados = await asyncio.gather(*(uma(m) for m in municipios))
    finally:
        await varredura.fechar()
    return [x for lista in resultados for x in lista]


def gravar_sem_canal(restantes: list, destino: Path = SEM_CANAL, dia: str | None = None) -> None:
    dia = dia or date.today().isoformat()
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["ibge", "municipio", "uf", "buscado_em"])
        for ibge, nome, uf, _ in sorted(restantes, key=lambda m: (m[2], m[1])):
            escritor.writerow([ibge, nome, uf, dia])


def principal() -> None:
    parser = argparse.ArgumentParser(description="Segunda varredura das cidades sem canal")
    parser.add_argument("--ibge-raw", type=Path, required=True)
    parser.add_argument("--limite", type=int)
    parser.add_argument("--conexoes", type=int, default=8)
    args = parser.parse_args()
    alvo = sem_canal(ler_ibge_raw(args.ibge_raw))
    if args.limite:
        alvo = alvo[: args.limite]
    print(f"{len(alvo)} cidades sem canal", flush=True)
    inicio = time.time()
    novos = asyncio.run(varrer(alvo, args.conexoes))
    ganhas = {x["ibge"] for x in novos}
    if not args.limite:
        with CATALOGO.open(encoding="utf-8", newline="") as f:
            atuais = list(csv.DictReader(f))
        gravar_catalogo(atuais + novos, CATALOGO)
        gravar_sem_canal([m for m in alvo if m[0] not in ganhas])
    else:
        print(json.dumps(novos, ensure_ascii=False, indent=1))
    com_sapl = {x["ibge"] for x in novos if x["tipo"] == "sapl"}
    print(f"ganharam canal: {len(ganhas)} (SAPL: {len(com_sapl)}); sem: {len(alvo) - len(ganhas)}")
    print(f"tempo: {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    principal()
