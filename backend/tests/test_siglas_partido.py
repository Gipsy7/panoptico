from app.partidos import SEM_PARTIDO, sigla_partido


def test_junta_grafias_da_mesma_sigla():
    for g in ("REP", "Rep.", "REPUBL", "Republicanos", "REPUBLICANO"):
        assert sigla_partido(g) == "REPUBLICANOS"
    assert sigla_partido("União") == sigla_partido("UNIAO") == sigla_partido("UB") == "UNIÃO"
    assert sigla_partido("PC DO B") == sigla_partido("PCdoB") == "PCdoB"
    assert sigla_partido("Podemos") == "PODE"
    assert sigla_partido("MDB-15") == "MDB"


def test_siglas_antigas_e_desconhecidas_ficam_como_vieram():
    assert sigla_partido("PMDB") == "PMDB"
    assert sigla_partido("DEM") == "DEM"
    assert sigla_partido(" XYZ ") == "XYZ"


def test_vazio_e_sem_partido():
    assert sigla_partido(None) is None
    assert sigla_partido("  ") is None
    assert sigla_partido("S/Partido") == SEM_PARTIDO
