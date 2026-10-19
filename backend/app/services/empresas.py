"""Cadastro de empresas por CNPJ (tabela `empresa`, da base aberta da Receita): completa o nome
que as fontes deixam vazio e diz em que município está um órgão ou entidade pública."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cnpj import normalizar_cnpj
from app.models import Empresa
from app.textos import sem_cpf

# Naturezas jurídicas da Receita que são do município (prefeitura, câmara, autarquia, fundação,
# fundo e órgão autônomo municipais). Consórcios públicos (1210, 1228) não entram: reúnem mais
# de um município.
NATUREZAS_MUNICIPAIS = frozenset(
    {
        "1031",  # Órgão Público do Poder Executivo Municipal
        "1066",  # Órgão Público do Poder Legislativo Municipal
        "1120",  # Autarquia Municipal
        "1155",  # Fundação Pública de Direito Público Municipal
        "1180",  # Órgão Público Autônomo Municipal
        "1244",  # Município
        "1279",  # Fundação Pública de Direito Privado Municipal
        "1309",  # Fundo Público da Administração Indireta Municipal
        "1333",  # Fundo Público da Administração Direta Municipal
    }
)
LOTE = 5_000


def _em_lotes(itens: list[str]) -> Iterable[list[str]]:
    for i in range(0, len(itens), LOTE):
        yield itens[i : i + LOTE]


def nomes(session: Session, cnpjs: Iterable[str | None]) -> dict[str, tuple[str | None, bool]]:
    """cnpj -> (razão social, nome omitido por conter CPF) das empresas conhecidas.
    CNPJs fora do cadastro não aparecem no resultado."""
    unicos = sorted({c for c in (normalizar_cnpj(x) for x in cnpjs if x) if c})
    resultado: dict[str, tuple[str | None, bool]] = {}
    for lote in _em_lotes(unicos):
        for cnpj, razao, omitido in session.execute(
            select(Empresa.cnpj, Empresa.razao_social, Empresa.nome_omitido).where(
                Empresa.cnpj.in_(lote)
            )
        ):
            resultado[cnpj] = (razao, omitido)
    return resultado


def nome_da_empresa(
    nome_da_fonte: str | None,
    cnpj: str | None,
    cadastro: dict[str, tuple[str | None, bool]],
) -> tuple[str | None, bool]:
    """(nome a mostrar, omitido por conter CPF). O nome da fonte, sem CPF, vale primeiro; só
    quando falta entra a razão social do cadastro. Sem CPF no cadastro nem na fonte, None."""
    nome = sem_cpf(nome_da_fonte)
    if nome:
        return nome, False
    achado = cadastro.get(normalizar_cnpj(cnpj) or "") if cnpj else None
    if achado is None:
        return None, False
    razao, omitido = achado
    return razao, bool(omitido and not razao)


def cnpj_para_ibge(
    session: Session, cnpjs: Iterable[str | None], so_municipais: bool = True
) -> dict[str, str]:
    """cnpj -> código IBGE do município onde a empresa está registrada na Receita.

    Com `so_municipais` (padrão), só os CNPJs de entes do município (natureza jurídica 124-4
    Município, 103-1 Órgão Público do Poder Executivo Municipal, 106-6 Legislativo, autarquias,
    fundações e fundos municipais): é o que liga uma transferência (ex.: emenda Pix) à cidade
    que a recebeu. Sem, qualquer empresa com município conhecido. CNPJ fora do cadastro, sem
    município ou (no padrão) de natureza não municipal não aparece."""
    unicos = sorted({c for c in (normalizar_cnpj(x) for x in cnpjs if x) if c})
    resultado: dict[str, str] = {}
    for lote in _em_lotes(unicos):
        consulta = select(Empresa.cnpj, Empresa.municipio_ibge).where(
            Empresa.cnpj.in_(lote), Empresa.municipio_ibge.is_not(None)
        )
        if so_municipais:
            consulta = consulta.where(Empresa.natureza_juridica.in_(NATUREZAS_MUNICIPAIS))
        resultado.update({c: ibge for c, ibge in session.execute(consulta) if ibge})
    return resultado


def ibge_do_cnpj(session: Session, cnpj: str | None, so_municipais: bool = True) -> str | None:
    """Município (IBGE) de um CNPJ; ver `cnpj_para_ibge`."""
    return cnpj_para_ibge(session, [cnpj], so_municipais).get(normalizar_cnpj(cnpj) or "")
