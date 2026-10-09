# ruff: noqa: E501  (recortes das páginas reais da ALERJ)
from ingestion.assembleias import alerj

# Recortes reais do site da ALERJ (09/10/2026).
LISTA = """
<div class="controle_deputado lider">
    <div class="imagem">
        <a href="/Deputados/PerfilDeputado/269?Legislatura=20"><img src="/Uploads/PerfilDeputado/Imagem/24022023_155116LuizPaulo.jpg" alt="LUIZ PAULO"></a>
    </div>
    <div class="descricao">
        <div class="partido">PSD</div>
        <div class="nome"><a href="/Deputados/PerfilDeputado/269?Legislatura=20">LUIZ PAULO</a></div>
    </div>
    <span></span>
</div>
<div class="controle_deputado">
    <div class="imagem">
        <a href="/Deputados/PerfilDeputado/464?Legislatura=20"><img src="/Uploads/PerfilDeputado/Imagem/x.jpg" alt="CELIA JORD&#195;O"></a>
    </div>
    <div class="descricao">
        <div class="partido">PL</div>
        <div class="nome"><a href="/Deputados/PerfilDeputado/464?Legislatura=20">CELIA JORD&#195;O</a></div>
    </div>
    <span></span>
</div>
<div class="controle_deputado lider">
    <div class="imagem">
        <a href="/Deputados/PerfilDeputado/269?Legislatura=20"><img src="/Uploads/PerfilDeputado/Imagem/24022023_155116LuizPaulo.jpg" alt="LUIZ PAULO"></a>
    </div>
    <div class="descricao">
        <div class="partido">PSD</div>
        <div class="nome"><a href="/Deputados/PerfilDeputado/269?Legislatura=20">LUIZ PAULO</a></div>
    </div>
</div>
"""
PERFIL = """
<div class="conteudo deputado">
  <div class="controle_sroll">
    <div class="descricao">
        <h1>Luiz Paulo</h1>
        <h2 class="margin_bottom_5">NASCIMENTO</h2>
        <p> 26 de dezembro de 1945</p>
        <h2 class="margin_bottom_5">CONTATO</h2>
        <p>(21) 2588-1259</p>
        <p>luizpaulo@alerj.rj.gov.br</p>
    </div>
  </div>
</div>
"""


def test_lista_e_perfil():
    lista = alerj.deputados(LISTA)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("269", "Luiz Paulo", "PSD"),  # repetido na lista, entra uma vez
        ("464", "Celia Jordão", "PL"),  # entidade HTML e caixa alta
    ]
    assert (
        lista[0]["foto"]
        == "https://www.alerj.rj.gov.br/Uploads/PerfilDeputado/Imagem/24022023_155116LuizPaulo.jpg"
    )
    assert alerj.perfil(PERFIL) == {
        "nome": "Luiz Paulo",
        "email": "luizpaulo@alerj.rj.gov.br",
        "telefone": "(21) 2588-1259",
    }
    assert alerj.perfil("<html></html>") == {"nome": None, "email": None, "telefone": None}


def test_decodificar_aceita_utf8_e_windows_1252():
    assert alerj._decodificar("Jordão".encode()) == "Jordão"
    assert alerj._decodificar("Jordão".encode("cp1252")) == "Jordão"
