"""Catálogo das fontes de dados, com a data da última carga bem-sucedida de cada uma."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao

CATALOGO = [
    {
        "dado": "Deputados federais em exercício",
        "orgao": "Câmara dos Deputados",
        "fontes": ["camara_deputados"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Senadores em exercício",
        "orgao": "Senado Federal",
        "fontes": ["senado_senadores"],
        "url": "https://legis.senado.leg.br/dadosabertos/",
    },
    {
        "dado": "Gastos do gabinete (cota parlamentar)",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_despesas", "senado_despesas"],
        "url": "https://www.camara.leg.br/transparencia/gastos-parlamentares",
    },
    {
        "dado": "Votações nominais (Plenário e comissões) e orientação do Governo",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_votacoes", "senado_votacoes", "senado_votacoes_comissoes"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Projetos de lei e autores",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_proposicoes", "camara_autores", "senado_proposicoes"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Temas das proposições (classificação oficial)",
        "orgao": "Câmara dos Deputados",
        "fontes": ["camara_temas"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Emendas parlamentares e quem recebeu",
        "orgao": "Controladoria-Geral da União (Portal da Transparência)",
        "fontes": ["transparencia_emendas"],
        "url": "https://portaldatransparencia.gov.br/emendas",
    },
    {
        "dado": "Candidaturas, bens declarados e contas de campanha",
        "orgao": "Tribunal Superior Eleitoral",
        "fontes": ["tse_candidaturas", "tse_bens", "tse_campanha"],
        "url": "https://dadosabertos.tse.jus.br/",
    },
    {
        "dado": "Lista de municípios",
        "orgao": "IBGE",
        "fontes": ["ibge_municipios"],
        "url": "https://servicodados.ibge.gov.br/api/docs/localidades",
    },
    {
        "dado": "Salário (subsídio) dos parlamentares",
        "orgao": "Congresso Nacional (Decreto Legislativo nº 172/2022)",
        "fontes": [],
        "url": "https://www2.camara.leg.br/legin/fed/decleg/2022/"
        "decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html",
    },
    {
        "dado": "CEP para cidade e estado (consultado na hora, não guardado)",
        "orgao": "ViaCEP",
        "fontes": [],
        "url": "https://viacep.com.br/",
    },
]


def listar(session: Session) -> list[dict]:
    ultimas = dict(
        session.execute(
            select(FonteIngestao.fonte, func.max(FonteIngestao.concluido_em))
            .where(FonteIngestao.status == "ok")
            .group_by(FonteIngestao.fonte)
        ).all()
    )
    resultado = []
    for item in CATALOGO:
        datas = [ultimas[f] for f in item["fontes"] if f in ultimas]
        resultado.append(
            {
                "dado": item["dado"],
                "orgao": item["orgao"],
                "url": item["url"],
                # A carga mais antiga entre as fontes do item: é até quando tudo está em dia.
                "atualizado_em": min(datas) if datas else None,
            }
        )
    return resultado
