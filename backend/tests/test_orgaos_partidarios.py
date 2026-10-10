from ingestion.tse import orgaos_partidarios as orgaos

BASE = {"DT_GERACAO": "03/10/2026", "SQ_ORGAO_PARTIDARIO": "1", "SQ_CARGO_MEMBRO": "10",
        "SG_PARTIDO": "PL", "NM_TIPO_ORGAO_PARTIDARIO": "ÓRGÃO PROVISÓRIO",
        "DS_TIPO_ABRANGENCIA": "MUNICIPAL", "SG_UF": "SC", "NM_MUNICIPIO": "URUBICI",
        "DS_CARGO_MEMBRO": "PRESIDENTE", "NR_TITULO_ELEITORAL_MEMBRO": "35020992275",
        "DT_INICIO_EXERCICIO_MEMBRO": "16/03/2024", "DS_SITU_EXERC_MEMBRO": "VIGENTE",
        "DS_SITU_EXERC_ORGAO_PARTIDARIO": "VIGENTE"}  # fmt: skip


def test_so_cargos_vigentes_de_quem_temos_pelo_titulo():
    linhas = [
        BASE,
        {**BASE, "SQ_CARGO_MEMBRO": "11", "DS_SITU_EXERC_MEMBRO": "NÃO VIGENTE"},
        {**BASE, "SQ_CARGO_MEMBRO": "12", "DS_SITU_EXERC_ORGAO_PARTIDARIO": "NÃO VIGENTE"},
        {**BASE, "SQ_CARGO_MEMBRO": "13", "NR_TITULO_ELEITORAL_MEMBRO": "999999999999"},
        {**BASE, "SQ_CARGO_MEMBRO": "14", "DT_INICIO_EXERCICIO_MEMBRO": "16/03/0208",
         "DS_TIPO_ABRANGENCIA": "NACIONAL", "DS_CARGO_MEMBRO": "TESOUREIRO"},
    ]  # fmt: skip
    eventos = orgaos.eventos(linhas, {"035020992275": 7})  # título com zeros à esquerda
    assert [(e["id_externo"], e["pessoa_id"]) for e in eventos] == [("1:10", 7), ("1:14", 7)]
    assert (
        eventos[0]["descricao"] == "Presidente do órgão provisório municipal do PL em Urubici (SC)"
    )
    assert eventos[0]["situacao"] == "vigente segundo o TSE em 03/10/2026"
    assert eventos[1]["data"] is None  # ano truncado no arquivo ("0208")
    assert eventos[1]["descricao"] == "Tesoureiro do órgão provisório nacional do PL"


def test_sha256_de_json_ignora_a_ordem_das_chaves():
    from ingestion import comum

    assert comum.sha256_de({"a": 1, "b": [1, 2]}) == comum.sha256_de({"b": [1, 2], "a": 1})
    assert comum.sha256_de({"a": 1}) != comum.sha256_de({"a": 2})
    assert comum.sha256_de(b"x") == comum.sha256_de(b"x")
