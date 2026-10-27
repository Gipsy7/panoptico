"""Leva o resultado da descoberta de sistemas (`data/cidades_sem_canal_sistemas.csv`) para o
catálogo de canais e tira dos "sem canal" as cidades que passaram a ter um.

Para cada cidade com site da câmara achado:
- `camara`: o endereço do site (também quando o site veda robôs: o link é para o cidadão, não
  lemos nada dele);
- `sapl`: quando a API do SAPL responde (a carga semanal do SAPL passa a ler a casa);
- `sistema_legislativo`: quando há leitor para o fornecedor (`ingestion.camaras.*`) e o
  conector já foi conferido contra a página real (`situacao = aberto`); a coluna `sistema` leva
  o nome do fornecedor e a URL é a que o leitor espera.

Idempotente: não repete linhas que já estão no catálogo. Uso:
    python -m ingestion.canais.aplicar_descoberta [--simular]
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from ingestion.canais.descobrir_sistemas import SAIDA, forte
from ingestion.canais.segunda_varredura import SEM_CANAL
from ingestion.canais.varredura import CATALOGO, gravar_catalogo

# Sistema da descoberta -> (sistema do catálogo, como montar a URL do leitor a partir do site).
LEITORES = {
    "sapl": ("sapl", None),
    "digitaliza": ("digitaliza", "raiz"),
    "camarasempapel": ("camarasempapel", "camarasempapel"),
    "webservicesistemas": ("webservicesistemas", "raiz"),
    "sts": ("sts", "sts"),
    "abase": ("cespro", "raiz"),
    "cespro": ("cespro", "raiz"),
    "icamaras": ("icamaras", "raiz"),
    "portalfacil": ("portalfacil", "raiz"),
    "rodape:Actcon.net": ("portalfacil", "raiz"),
    "ingadigital": ("ingadigital", "raiz"),
}


def url_do_leitor(url: str, como: str | None) -> str:
    raiz = url.rstrip("/")
    if como == "sts":
        return raiz + "/acessoinformacao/parlamentares"
    return raiz + "/"


def linhas_novas(descobertas: list[dict], dia: str) -> list[dict]:
    novas = []
    for d in descobertas:
        if not d["url"]:
            continue
        host = d["url"].split("/")[2]
        if d["situacao"] == "bloqueado" and not forte(host, d["cidade"], d["uf"]):
            continue  # domínio fraco e página não aberta: sem prova de que é da cidade
        base = {
            "ibge": d["ibge"],
            "municipio": d["cidade"],
            "uf": d["uf"],
            "verificado_em": dia,
        }
        if d["sistema"] == "sapl":
            novas.append({**base, "tipo": "camara", "url": d["url"], "sistema": ""})
            novas.append({**base, "tipo": "sapl", "url": d["url"], "sistema": "sapl"})
            continue
        novas.append({**base, "tipo": "camara", "url": d["url"], "sistema": ""})
        leitor = LEITORES.get(d["sistema"])
        if leitor and d["situacao"] == "aberto":
            sistema, como = leitor
            novas.append(
                {
                    **base,
                    "tipo": "sistema_legislativo",
                    "url": url_do_leitor(d["url"], como),
                    "sistema": sistema,
                }
            )
    return novas


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--simular", action="store_true")
    args = parser.parse_args()
    with SAIDA.open(encoding="utf-8", newline="") as f:
        descobertas = list(csv.DictReader(f))
    with CATALOGO.open(encoding="utf-8", newline="") as f:
        atuais = list(csv.DictReader(f))
    ja = {(x["ibge"], x["tipo"]) for x in atuais}
    novas = [
        n
        for n in linhas_novas(descobertas, date.today().isoformat())
        if (n["ibge"], n["tipo"]) not in ja
    ]
    ganhas = {n["ibge"] for n in novas if n["tipo"] in ("camara", "sapl")}
    print(f"{len(novas)} linhas novas; {len(ganhas)} cidades passam a ter canal")
    if args.simular:
        return
    gravar_catalogo(atuais + novas, CATALOGO)
    with Path(SEM_CANAL).open(encoding="utf-8", newline="") as f:
        sem = list(csv.DictReader(f))
    restantes = [r for r in sem if r["ibge"] not in ganhas]
    with Path(SEM_CANAL).open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=["ibge", "municipio", "uf", "buscado_em"])
        escritor.writeheader()
        escritor.writerows(restantes)
    print(f"sem canal: {len(sem)} -> {len(restantes)}")


if __name__ == "__main__":
    principal()
