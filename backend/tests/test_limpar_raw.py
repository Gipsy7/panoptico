from ingestion.limpar_raw import limpar


def test_limpar_mantem_os_mais_recentes_por_fonte_e_ano(tmp_path):
    fonte = tmp_path / "camara_despesas"
    fonte.mkdir()
    nomes = [
        "2025_2026-10-01_060000.zip",
        "2025_2026-10-02_060000.zip",
        "2025_2026-10-03_060000.zip",
        "2026_2026-10-01_060000.zip",
        "2026_2026-10-03_060000.zip",
        "leia-me.txt",
    ]
    for nome in nomes:
        (fonte / nome).write_text("x")

    apagados = limpar(tmp_path, manter=2)

    assert [a.name for a in apagados] == ["2025_2026-10-01_060000.zip"]
    assert sorted(p.name for p in fonte.iterdir()) == sorted(nomes[1:])
