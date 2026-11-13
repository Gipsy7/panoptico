from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import case, select

from app.db import Sessao
from app.models import CanalOficial, Municipio
from app.schemas import (
    CanaisResposta,
    ContasMunicipioResposta,
    FornecedoresPncpResposta,
    FornecedoresResposta,
    MunicipioInfo,
)
from app.schemas.agro import AgroMunicipio
from app.schemas.comparar_cidades import CidadesParecidas, Vocacoes
from app.schemas.emendas_municipio import EmendasMunicipioCompleta
from app.schemas.emprego import EmpregoMunicipio
from app.schemas.ideb import IdebMunicipio
from app.schemas.internet import InternetMunicipio
from app.schemas.obras import ObrasMunicipio, ObrasPorUf
from app.schemas.pib import PibMunicipio
from app.schemas.repasses_estaduais import RepassesEstaduaisResposta
from app.schemas.saneamento import SaneamentoMunicipio
from app.schemas.saude_cnes import SaudeMunicipio
from app.schemas.seguranca import SegurancaMunicipio
from app.schemas.tempo import LinhaDoTempo
from app.services import (
    agro,
    comparar_cidades,
    contas,
    contratos_pncp,
    emendas,
    emprego,
    fornecedores,
    ideb,
    internet,
    obras,
    pib,
    repasses_estaduais,
    saneamento,
    saude_cnes,
    seguranca,
    tempo,
)
from app.services.texto_busca import normalizar

router = APIRouter()


@router.get("/municipios/{ibge}/emendas", response_model=EmendasMunicipioCompleta)
def emendas_do_municipio(ibge: str, session: Sessao) -> dict:
    """Emendas pagas à cidade por tipo e autor, previsto nos planos Pix e convênios."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return emendas.resumo_municipio(session, municipio)


@router.get("/municipios/{ibge}/contas", response_model=ContasMunicipioResposta)
def contas_do_municipio(ibge: str, session: Sessao) -> dict:
    """Contas anuais da prefeitura no SICONFI: receita, despesa e áreas."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = contas.resumo(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem contas entregues ao Tesouro para este município.")
    return resultado


@router.get("/municipios/{ibge}/repasses-estaduais", response_model=RepassesEstaduaisResposta)
def repasses_estaduais_do_municipio(ibge: str, session: Sessao) -> dict:
    """Quanto o governo do estado repassou à prefeitura, por tipo (SICONFI, DCA)."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return repasses_estaduais.resumo(session, municipio)


@router.get("/municipios/{ibge}/fornecedores", response_model=FornecedoresResposta)
def fornecedores_do_municipio(ibge: str, session: Sessao) -> dict:
    """Para quem a prefeitura e a câmara pagaram (onde o Tribunal de Contas publica)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = fornecedores.resumo(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem dados de fornecedores para este município.")
    return resultado


ORDEM_CANAIS = [
    "prefeitura",
    "camara",
    "sapl",
    "sistema_legislativo",
    "transparencia_prefeitura",
    "transparencia_camara",
]


@router.get("/municipios/{ibge}/canais", response_model=CanaisResposta)
def canais_do_municipio(ibge: str, session: Sessao) -> dict:
    """Sites oficiais da cidade, do catálogo revisado (data/canais_oficiais.csv)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    canais = session.scalars(select(CanalOficial).where(CanalOficial.municipio_ibge == ibge)).all()
    canais = sorted(
        canais, key=lambda c: ORDEM_CANAIS.index(c.tipo) if c.tipo in ORDEM_CANAIS else 99
    )
    return {"itens": canais}


@router.get("/municipios/{ibge}/obras", response_model=ObrasMunicipio)
def obras_do_municipio(ibge: str, session: Sessao) -> dict:
    """Obras federais do Obrasgov.br na cidade, por situação, com o percentual executado."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return obras.do_municipio(session, ibge)


@router.get("/municipios/{ibge}/ideb", response_model=IdebMunicipio)
def ideb_do_municipio(ibge: str, session: Sessao) -> dict:
    """IDEB da cidade por etapa e rede, com o do estado e o do Brasil na mesma rede (INEP)."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return ideb.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/pib", response_model=PibMunicipio)
def pib_do_municipio(ibge: str, session: Sessao) -> dict:
    """PIB da cidade (IBGE), com o PIB por morador do estado e do Brasil no mesmo ano."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return pib.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/agro", response_model=AgroMunicipio)
def agro_do_municipio(ibge: str, session: Sessao) -> dict:
    """Lavouras da cidade (IBGE, PAM): valor da produção e os produtos que mais pesam."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return agro.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/emprego", response_model=EmpregoMunicipio)
def emprego_do_municipio(ibge: str, session: Sessao) -> dict:
    """Trabalho formal da cidade (IBGE, CEMPRE): empresas, pessoas ocupadas e salário médio."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return emprego.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/parecidas", response_model=CidadesParecidas)
def cidades_parecidas(ibge: str, session: Sessao) -> dict:
    """As cidades com a população mais próxima, lado a lado (não é ranking)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return comparar_cidades.parecidas(session, ibge)


@router.get("/municipios/{ibge}/vocacoes", response_model=Vocacoes)
def vocacoes_da_cidade(ibge: str, session: Sessao) -> dict:
    """O peso de cada atividade aqui e no Brasil (PIB e pessoas ocupadas)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return comparar_cidades.vocacoes(session, ibge)


@router.get("/municipios/{ibge}/internet", response_model=InternetMunicipio)
def internet_da_cidade(ibge: str, session: Sessao) -> dict:
    """Banda larga fixa (Anatel) por 100 moradores, com o estado e o Brasil."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return internet.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/saneamento", response_model=SaneamentoMunicipio)
def saneamento_da_cidade(ibge: str, session: Sessao) -> dict:
    """Água, esgoto e lixo no Censo 2022 (IBGE), com o estado e o Brasil."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return saneamento.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/seguranca", response_model=SegurancaMunicipio)
def seguranca_da_cidade(ibge: str, session: Sessao) -> dict:
    """Homicídios de moradores (SIM/DATASUS) ano a ano, com o estado e o Brasil."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return seguranca.do_municipio(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/saude", response_model=SaudeMunicipio)
def saude_da_cidade(ibge: str, session: Sessao) -> dict:
    """Leitos, unidades básicas e hospitais (CNES/DATASUS), com o estado e o Brasil."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return saude_cnes.do_lugar(session, ibge, municipio.uf)


@router.get("/municipios/{ibge}/tempo", response_model=LinhaDoTempo)
def tempo_da_cidade(ibge: str, session: Sessao) -> dict:
    """Séries anuais da cidade no mesmo eixo de anos, com prefeitos e governadores."""
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return tempo.da_cidade(session, ibge, municipio.uf)


@router.get("/obras/estados", response_model=ObrasPorUf)
def obras_por_estado(session: Sessao) -> dict:
    """Obras federais por estado e situação (Obrasgov.br)."""
    return obras.resumo_ufs(session)


@router.get("/municipios/busca", response_model=list[MunicipioInfo])
def buscar_municipio(
    q: Annotated[str, Query(min_length=2, max_length=80)],
    session: Sessao,
) -> list[Municipio]:
    """Cidades pelo nome, sem acento nem caixa (a busca da home): primeiro as que começam com o
    texto, depois as que o contêm; no máximo 8."""
    termo = " ".join(normalizar(q).upper().split())
    if len(termo) < 2:
        return []
    comeca = Municipio.nome_chave.startswith(termo, autoescape=True)
    return list(
        session.scalars(
            select(Municipio)
            .where(Municipio.nome_chave.contains(termo, autoescape=True))
            .order_by(case((comeca, 0), else_=1), Municipio.nome_chave, Municipio.uf)
            .limit(8)
        )
    )


@router.get("/municipios", response_model=list[MunicipioInfo])
def municipios_da_uf(
    uf: Annotated[str, Query(min_length=2, max_length=2)],
    session: Sessao,
) -> list[Municipio]:
    return list(
        session.scalars(
            select(Municipio).where(Municipio.uf == uf.upper()).order_by(Municipio.nome_chave)
        )
    )


@router.get("/municipios/{ibge}/fornecedores-pncp", response_model=FornecedoresPncpResposta)
def fornecedores_pncp_do_municipio(ibge: str, session: Sessao) -> dict:
    """Maiores fornecedores dos órgãos municipais no PNCP, no ano mais recente."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = contratos_pncp.maiores_do_municipio(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem contratos do PNCP para este município.")
    return resultado
