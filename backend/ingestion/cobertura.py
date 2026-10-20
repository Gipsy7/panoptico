"""Régua de cobertura: o que o Panóptico mostra (ou não) de cada cargo, em cada Estado.

Só leitura e sem banco. Deriva a matriz dos arquivos versionados:
- `backend/ingestion/fontes.toml` (degrau de acesso de cada fonte: `brasil` = o site bloqueia IP
  de fora do Brasil, então só o acervo local carrega);
- `data/pendencias_cobertura.csv`, `data/canais_oficiais.csv`, `data/cidades_sem_canal.csv`;
- o que cada conector de `backend/ingestion/assembleias/*.py` carrega (tabela `ASSEMBLEIAS`
  abaixo, conferida com a descrição de cada módulo);
- `docs/pedidos/` (pedidos de acesso já redigidos).

Saída: `data/cobertura_matriz.csv`, uma linha por (uf, casa, cargo, seção), com situação:
  sim | parcial | bloqueado | pedido | sem_fonte.
Na dúvida, `sem_fonte` com o motivo. Uso: `python -m ingestion.cobertura`.
"""

import csv
import tomllib
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FONTES = RAIZ / "backend" / "ingestion" / "fontes.toml"
DADOS = RAIZ / "data"
SAIDA = DADOS / "cobertura_matriz.csv"

UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]  # fmt: skip
SECOES = [
    "gastos", "votos", "presenca", "projetos", "emendas", "salario", "agenda", "atos",
    "bens_campanha",
]  # fmt: skip
COLUNAS = ["uf", "casa", "cargo", "secao", "situacao", "motivo", "fonte", "pedido"]
SITUACOES = {"sim", "parcial", "bloqueado", "pedido", "sem_fonte"}
URL_ALEP = "https://webservices.assembleia.pr.leg.br/api/public/"
URL_ALEP_VERBA = (
    "https://transparencia.assembleia.pr.leg.br/receitas-e-despesas/verbas-de-ressarcimento"
)

# Assembleias: fonte (nome em fontes.toml) e o que o conector carrega. Conferido com o
# docstring de cada módulo em ingestion/assembleias/. Seção ausente = o conector não carrega.
SAPL_UFS = ["AC", "AL", "AM", "PB", "PI", "RO", "RR", "TO"]
ASSEMBLEIAS: dict[str, tuple[str, set[str]]] = {
    **{uf: ("sapl_assembleias", {"projetos", "votos", "presenca"}) for uf in SAPL_UFS},
    "AP": ("alap", {"projetos"}),
    "BA": ("alba", {"projetos", "presenca"}),
    "CE": ("alece", {"projetos"}),
    "DF": ("cldf", {"projetos"}),
    "ES": ("ales", {"projetos", "presenca"}),
    "GO": ("alego", {"gastos"}),
    "MA": ("alema", {"projetos"}),
    "MG": ("almg", {"projetos", "gastos"}),
    "MS": ("alems", {"gastos"}),
    "MT": ("almt", set()),
    "PA": ("alepa", set()),
    "PE": ("alepe", {"projetos"}),
    "PR": ("alep", {"votos", "presenca"}),  # projetos e gastos: pedido (API travada, reCAPTCHA)
    "RJ": ("alerj", set()),
    "RN": ("alrn", {"projetos"}),
    "RS": ("alrs", {"projetos", "votos", "presenca", "gastos"}),
    "SC": ("alesc", {"projetos", "gastos", "presenca"}),
    "SE": ("alese", {"presenca"}),
    "SP": ("alesp", {"projetos", "gastos"}),
}
ROTULO = {
    "gastos": "gastos do gabinete e da cota",
    "votos": "votos nominais",
    "presenca": "presença em plenário",
    "projetos": "projetos de lei",
}
# Pedidos redigidos (docs/pedidos/) que cobrem uma seção de uma assembleia.
PEDIDO_ASSEMBLEIA = {
    ("MG", "votos"): "almg_alesp_votos_presenca.md",
    ("MG", "presenca"): "almg_alesp_votos_presenca.md",
    ("SP", "votos"): "almg_alesp_votos_presenca.md",
    ("SP", "presenca"): "almg_alesp_votos_presenca.md",
    ("MT", "projetos"): "almt_proposicoes.md",
    ("MT", "votos"): "almt_proposicoes.md",
    ("MT", "presenca"): "almt_proposicoes.md",
    ("PA", "projetos"): "alepa_proposicoes.md",
    ("PA", "votos"): "alepa_proposicoes.md",
    ("PR", "projetos"): "alep_certificado.md",
    ("PR", "gastos"): "alep_certificado.md",
}
MOTIVO_PEDIDO = {
    "MG": "A Casa não publica em dados abertos; pedido de acesso redigido.",
    "SP": "A Casa não publica em dados abertos; pedido de acesso redigido.",
    "MT": "O sistema da Casa exige senha de fornecedor e o arquivo de regras do site (robots.txt) "
    "veda a pesquisa; pedimos acesso público.",
    "PA": "A pesquisa do portal só funciona digitando no navegador; pedimos os dados em "
    "formato aberto.",
}
EMENDAS_27 = "emendas_estaduais_27_ufs.md"


def _ler_csv(nome: str) -> list[dict[str, str]]:
    with (DADOS / nome).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _acessos() -> dict[str, str]:
    with FONTES.open("rb") as f:
        return {x["nome"]: x.get("acesso", "aberto") for x in tomllib.load(f)["fonte"]}


def _linha(uf, casa, cargo, secao, situacao, motivo, fonte="", pedido=""):
    assert situacao in SITUACOES and secao in SECOES, (situacao, secao)
    valores = [uf, casa, cargo, secao, situacao, motivo, fonte, pedido]
    return dict(zip(COLUNAS, valores, strict=True))


def _secao_legislativa(uf, secao, fonte, carrega, brasil):
    """(situação, motivo, fonte, pedido) de projetos/votos/presença/gastos de uma assembleia."""
    pedido = PEDIDO_ASSEMBLEIA.get((uf, secao), "")
    r = ROTULO[secao]
    if secao in carrega:
        if brasil:
            m = (
                f"O site já lê {r}, mas o site da Casa só responde a acessos feitos do "
                "Brasil; por isso só dá para atualizar a partir de um computador no Brasil, "
                "e o site no ar não se atualiza sozinho."
            )
            return "bloqueado", m, fonte, ""
        m = f"Carregamos {r} do site oficial da Casa."
        if uf == "SP" and secao == "projetos":
            m += " Votos nominais de Plenário e presença não saem dos dados abertos."
        return "sim", m, fonte, ""
    if uf == "PR" and secao == "projetos":
        m = (
            "Os projetos só estão no sistema de consulta da ALEP, que tem um certificado de "
            "segurança sem validade reconhecida e recusa o acesso; não desligamos a "
            "verificação nem contornamos. Pedido redigido."
        )
        return "pedido", m, URL_ALEP, pedido
    if uf == "PR" and secao == "gastos":
        m = (
            "A consulta da verba de ressarcimento exige verificação de humano (reCAPTCHA); "
            "não contornamos. Pedimos os dados em planilha."
        )
        return "pedido", m, URL_ALEP_VERBA, pedido
    if uf == "SC" and secao == "votos":
        m = (
            "As votações vistas no e-Legis são simbólicas; o extrato de voto nominal não foi "
            "localizado numa sessão com voto nominal."
        )
        return "sem_fonte", m, fonte, ""
    if uf == "SP" and secao == "votos":
        m = (
            "Só o voto nas comissões permanentes; o voto no Plenário não está nos dados "
            "abertos (pedido de acesso redigido)."
        )
        return "parcial", m, fonte, pedido
    if pedido:
        return "pedido", MOTIVO_PEDIDO[uf], fonte, pedido
    if uf == "MS" and secao == "projetos":
        m = (
            "O sistema de proposições exige uma verificação que barra acesso por programa; "
            "não contornamos."
        )
        return "bloqueado", m, fonte, ""
    if uf == "RJ":
        m = "O processo legislativo roda num sistema antigo que não entrega dados por consulta."
        return "sem_fonte", m, fonte, ""
    return "sem_fonte", f"O site ainda não lê {r} desta Casa.", fonte, ""


def _assembleia(uf, acessos) -> list[dict]:
    fonte, carrega = ASSEMBLEIAS[uf]
    casa = "CLDF" if uf == "DF" else f"AL{uf}"
    cargo = "deputado distrital" if uf == "DF" else "deputado estadual"
    brasil = bool(fonte) and acessos.get(fonte) == "brasil"
    linhas = []
    for secao in SECOES:
        if secao in ROTULO:
            dados = _secao_legislativa(uf, secao, fonte, carrega, brasil)
        elif secao == "emendas":
            m = "Sem fonte aberta de emendas estaduais; pedido de acesso redigido (ADPF 854)."
            pedido = EMENDAS_27
            dados = ("pedido", m, "", pedido)
            if uf == "SC":
                m = (
                    "Emendas impositivas da ALESC executadas por convênio ou termo de fomento "
                    "(SC Transferências, CGE/SC, desde 2022): autor, cidade, quem recebeu, "
                    "previsto, empenhado e pago. Repasses fundo a fundo e às prefeituras ficam "
                    "de fora; pedidos à ALESC e ao TCE/SC seguem para a base completa."
                )
                pedido = f"alesc_emendas_impositivas.md; tcesc_painel_emendas.md; {EMENDAS_27}"
                dados = ("parcial", m, "sctransferencias_emendas", pedido)
        elif secao == "salario":
            dados = ("sem_fonte", "Subsídio e folha dos deputados estaduais não coletados.", "", "")
        elif secao == "agenda":
            dados = ("sem_fonte", "Nenhuma fonte de agenda de deputados estaduais.", "", "")
        elif secao == "atos":
            dados = ("sem_fonte", "Diários oficiais estaduais não são lidos.", "", "")
        else:
            dados = ("sim", "Bens e campanha declarados ao TSE.", "tse_bens; tse_campanha", "")
        linhas.append(_linha(uf, casa, cargo, secao, *dados))
    return linhas


def _federal(uf, casa, cargo, camara: bool) -> list[dict]:
    p = "camara" if camara else "senado"
    if camara:
        presenca = (
            "parcial",
            "Presença nas votações; as justificativas de ausência não são publicadas "
            "(pedido de acesso redigido).",
            "camara_votacoes",
            "camara_justificativas_ausencia.md",
        )
    else:
        presenca = ("sim", "Presença nas votações.", "senado_votacoes", "")
    emendas_fonte = "transparencia_emendas; transferegov_convenios; transferegov_especiais"
    dados = {
        "gastos": ("sim", "Cota parlamentar e gastos do gabinete.", f"{p}_despesas", ""),
        "votos": ("sim", "Voto de cada votação nominal.", f"{p}_votacoes", ""),
        "presenca": presenca,
        "projetos": ("sim", "Projetos de lei de autoria.", f"{p}_proposicoes", ""),
        "emendas": ("sim", "Emendas e dinheiro enviado às cidades.", emendas_fonte, ""),
        "salario": ("sem_fonte", "Subsídio e folha do gabinete não coletados.", "", ""),
        "agenda": ("sem_fonte", "Nenhuma fonte de agenda de parlamentares.", "", ""),
        "atos": (
            "parcial",
            "Nomeações no Diário Oficial da União, só depois de revisão humana.",
            "dou_atos",
            "",
        ),
        "bens_campanha": (
            "sim",
            "Bens e campanha declarados ao TSE.",
            "tse_bens; tse_campanha",
            "",
        ),
    }
    return [_linha(uf, casa, cargo, s, *dados[s]) for s in SECOES]


def _executivo(uf, casa, cargo, extra: dict[str, tuple]) -> list[dict]:
    base = {
        "gastos": ("sem_fonte", "Gastos do governo não coletados para este cargo.", "", ""),
        "projetos": ("sem_fonte", "Projetos enviados ao Legislativo não coletados.", "", ""),
        "emendas": ("sem_fonte", "Sem fonte de emendas para este cargo.", "", ""),
        "salario": ("sem_fonte", "Subsídio do cargo não coletado.", "", ""),
        "agenda": ("sem_fonte", "Nenhuma fonte de agenda coletada.", "", ""),
        "atos": ("sem_fonte", "Diários oficiais deste nível não são lidos.", "", ""),
        "bens_campanha": (
            "sim",
            "Bens e campanha declarados ao TSE.",
            "tse_bens; tse_campanha",
            "",
        ),
    }
    base.update(extra)
    return [_linha(uf, casa, cargo, s, *base[s]) for s in SECOES if s not in ("votos", "presenca")]


def _prefeitos() -> dict[str, tuple[int, int]]:
    com_canal: dict[str, set] = defaultdict(set)
    todos: dict[str, set] = defaultdict(set)
    for r in _ler_csv("canais_oficiais.csv"):
        todos[r["uf"]].add(r["ibge"])
        if r["tipo"] in ("prefeitura", "camara", "sapl"):
            com_canal[r["uf"]].add(r["ibge"])
    for r in _ler_csv("cidades_sem_canal.csv"):
        todos[r["uf"]].add(r["ibge"])
    return {uf: (len(com_canal[uf]), len(todos[uf])) for uf in UFS}


def _prefeito(uf, n, total) -> list[dict]:
    pref = f"{n} de {total} municípios com canal oficial achado. "
    gastos = (
        "parcial",
        pref + "Contas da cidade (Tesouro Nacional, SICONFI), sem pagamento por fornecedor.",
        "siconfi_contas",
        "",
    )
    if uf == "SP":
        gastos = (
            "sim",
            pref + "Contas da cidade e pagamento a fornecedores (TCE-SP).",
            "siconfi_contas; tce_sp",
            "",
        )
    elif uf == "RS":
        gastos = (
            "bloqueado",
            pref + "Pagamento a fornecedores (TCE-RS): o órgão só responde a acessos feitos "
            "do Brasil, então só dá para atualizar a partir de um computador no Brasil.",
            "siconfi_contas; tce_rs",
            "",
        )
    elif uf == "MG":
        gastos = (
            "pedido",
            pref + "O TCE-MG só entrega os dados com verificação de humano (reCAPTCHA); "
            "pedido de acesso redigido.",
            "siconfi_contas; tce_mg",
            "tce_mg.md",
        )
    extra = {
        "gastos": gastos,
        "emendas": (
            "parcial",
            pref + "Só emendas federais recebidas pela cidade; estaduais sem fonte.",
            "transparencia_emendas",
            "",
        ),
        "salario": ("sem_fonte", pref + "Subsídio do prefeito não coletado.", "", ""),
        "agenda": ("sem_fonte", pref + "Nenhuma fonte de agenda coletada.", "", ""),
        "atos": (
            "parcial",
            pref + "Nomeações em diários municipais, só nas cidades cobertas pelo Querido "
            "Diário e depois de revisão humana.",
            "querido_diario_atos",
            "",
        ),
        "bens_campanha": (
            "sim",
            pref + "Bens e campanha declarados ao TSE.",
            "tse_bens; tse_campanha",
            "",
        ),
        "projetos": ("sem_fonte", pref + "Projetos do Executivo municipal não coletados.", "", ""),
    }
    return _executivo(uf, f"Prefeituras de {uf}", "prefeito", extra)


def montar() -> list[dict]:
    acessos = _acessos()
    prefeitos = _prefeitos()
    linhas: list[dict] = []
    for uf in UFS:
        linhas += _assembleia(uf, acessos)
        linhas += _federal(uf, "Câmara dos Deputados", "deputado federal", True)
        linhas += _federal(uf, "Senado Federal", "senador", False)
        msg = "Sem fonte aberta de emendas estaduais; pedido de acesso redigido (ADPF 854)."
        linhas += _executivo(
            uf,
            f"Governo de {uf}",
            "governador",
            {
                "emendas": ("pedido", msg, "", EMENDAS_27),
                "gastos": (
                    "parcial",
                    "Contas do estado (Tesouro Nacional, SICONFI): receita e despesa por área, com "
                    "a média dos estados; sem pagamento por fornecedor.",
                    "siconfi_contas_estados",
                    "",
                ),
            },
        )
        linhas += _prefeito(uf, *prefeitos[uf])
    agenda = (
        "parcial",
        "Agenda de ministros e do vice-presidente (e-Agendas, CGU, arquivo aberto desde "
        "10/2022); a agenda do próprio presidente da República não consta nessa base.",
        "eagendas",
        "",
    )
    linhas += _executivo(
        "BR",
        "Presidência da República",
        "presidente",
        {
            "gastos": (
                "parcial",
                "Cartão de pagamento do governo e viagens a serviço de quem acompanhamos.",
                "cgu_cpgf; cgu_viagens",
                "",
            ),
            "agenda": agenda,
            "atos": (
                "parcial",
                "Atos no Diário Oficial da União, só depois de revisão humana.",
                "dou_atos",
                "",
            ),
            "emendas": ("sem_fonte", "O cargo não apresenta emendas.", "", ""),
        },
    )
    return linhas


def escrever(linhas: list[dict], destino: Path = SAIDA) -> None:
    with destino.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def resumo(linhas: list[dict]) -> str:
    por_sit: dict[str, int] = defaultdict(int)
    for x in linhas:
        por_sit[x["situacao"]] += 1
    return ", ".join(f"{k}={por_sit[k]}" for k in sorted(SITUACOES))


def main() -> None:
    linhas = montar()
    escrever(linhas)
    print(f"{len(linhas)} células em {SAIDA}: {resumo(linhas)}")


if __name__ == "__main__":
    main()
