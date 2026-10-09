import csv
import io
import zipfile
from datetime import date

from ingestion.transparencia import sancoes

COLUNAS = ["CADASTRO", "CÓDIGO DA SANÇÃO", "TIPO DE PESSOA", "CPF OU CNPJ DO SANCIONADO",
           "NOME DO SANCIONADO", "NÚMERO DO PROCESSO", "CATEGORIA DA SANÇÃO", "DATA INÍCIO SANÇÃO",
           "DATA FINAL SANÇÃO", "ÓRGÃO SANCIONADOR", "FUNDAMENTAÇÃO LEGAL"]  # fmt: skip
# Linhas reais dos arquivos de 08/10/2026 (CPFs trocados), mais uma empresa.
CEIS = [
    ["CEIS", "293234", "F", "08822750896", "SERGIO DUDA DA CRUZ", "00001259120048260627",
     "Impedimento/proibição de contratar com prazo determinado", "30/11/2021", "30/11/2029",
     "Tribunal de Justiça do Estado de São Paulo / 1º Grau - TJSP",
     "LEI 8429 - ART. 12 - INDEPENDENTEMENTE DAS SANÇÕES PENAIS, CIVIS E ADMINISTRATIVAS"],
    ["CEIS", "1", "J", "14286903000195", "SALOC SERVICOS", "x", "Multa", "", "", "Petrobras", ""],
]  # fmt: skip
CEAF = [
    ["CEAF", "270853", "F", "***.918.517-**", "TELMO ABRANTES", "10768.000360/2014-05",
     "Demissão", "27/05/2019", "", "Ministério da Economia",
     "ESTATUTO - ART. 132, IV - IMPROBIDADE ADMINISTRATIVA;ESTATUTO - ART. 117, IX - VALER-SE"],
]  # fmt: skip


def _csv_zip(nome: str, linhas: list) -> bytes:
    texto = io.StringIO()
    escritor = csv.writer(texto, delimiter=";")
    escritor.writerow(COLUNAS)
    escritor.writerows(linhas)
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr(nome, texto.getvalue().encode("latin-1"))
    return saida.getvalue()


def _bruto() -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("CEIS.zip", _csv_zip("20261008_CEIS.csv", CEIS))
        z.writestr("CNEP.zip", _csv_zip("20261008_CNEP.csv", []))
        z.writestr("CEAF.zip", _csv_zip("20261008_Expulsoes.csv", CEAF))
    return saida.getvalue()


def _registros():
    bruto = _bruto()
    return [
        r
        for c in ("CEIS", "CNEP", "CEAF")
        for r in sancoes.normalizar(c, sancoes.ler_zip(bruto, c))
    ]


def test_normalizar_so_pessoas_fisicas_e_cpf_mascarado():
    registros = _registros()
    assert [(r["cadastro"], r["cpf"], r["cpf_meio"]) for r in registros] == [
        ("CEIS", "08822750896", "227508"),
        ("CEAF", None, "918517"),
    ]
    ceis, ceaf = registros
    assert ceis["processo"] == "0000125-91.2004.8.26.0627"  # número do CNJ formatado
    assert ceaf["processo"] == "10768.000360/2014-05"  # processo administrativo, como veio
    assert ceaf["fundamentos"] == "ESTATUTO - ART. 132, IV; ESTATUTO - ART. 117, IX"
    assert sancoes.situacao(ceis, date(2026, 10, 9)) == "vigente até 30/11/2029"
    assert sancoes.situacao(ceaf, date(2026, 10, 9)) == "sem data final informada"
    assert sancoes.descricao(ceis) == (
        "Impedimento/proibição de contratar com prazo determinado, aplicada por Tribunal de "
        "Justiça do Estado de São Paulo / 1º Grau - TJSP. Fundamento: LEI 8429 - ART. 12. "
        "Registro nº 293234 no Cadastro de Empresas e Pessoas Inidôneas e Suspensas (CEIS), da CGU."
    )


def test_ligar_so_por_chave_forte():
    ceis, ceaf = _registros()
    pessoas = [
        (1, "08822750896", "SERGIO DUDA DA CRUZ"),
        (2, "11191851700", "TELMO ABRANTES"),  # 6 dígitos do meio + nome iguais
        (3, None, "TELMO ABRANTES"),  # sem CPF: o nome sozinho não liga
    ]
    assert [(r["codigo"], p, regra) for r, p, regra in sancoes.ligar([ceis, ceaf], pessoas)] == [
        ("293234", 1, "cpf"),
        ("270853", 2, "cpf_parcial_nome"),
    ]
    # Dois com os mesmos dígitos e o mesmo nome: ambíguo, não liga.
    pessoas.append((4, "99991851799", "TELMO ABRANTES"))
    assert len(sancoes.ligar([ceaf], pessoas)) == 0
