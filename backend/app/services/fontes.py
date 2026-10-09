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
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_temas", "senado_temas"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Emendas parlamentares e quem recebeu",
        "orgao": "Controladoria-Geral da União (Portal da Transparência)",
        "fontes": ["transparencia_emendas"],
        "url": "https://portaldatransparencia.gov.br/emendas",
    },
    {
        "dado": "Eleitos (do vereador ao presidente), bens, contas de campanha, votos, "
        "redes e fotos",
        "orgao": "Tribunal Superior Eleitoral",
        "fontes": [
            "tse_candidaturas",
            "tse_bens",
            "tse_campanha",
            "tse_redes",
            "tse_votos",
            "tse_fotos",
        ],
        "url": "https://dadosabertos.tse.jus.br/",
    },
    {
        "dado": "Contas anuais das prefeituras (receita, despesa e áreas)",
        "orgao": "Tesouro Nacional (SICONFI)",
        "fontes": ["siconfi_contas"],
        "url": "https://siconfi.tesouro.gov.br/",
    },
    {
        "dado": "Para quem a prefeitura e a câmara pagaram (São Paulo)",
        "orgao": "Tribunal de Contas do Estado de São Paulo",
        "fontes": ["tce_sp"],
        "url": "https://transparencia.tce.sp.gov.br/conjunto-de-dados",
    },
    {
        "dado": "Para quem a prefeitura e a câmara pagaram (Rio Grande do Sul)",
        "orgao": "Tribunal de Contas do Estado do Rio Grande do Sul",
        "fontes": ["tce_rs"],
        "url": "https://dados.tce.rs.gov.br/",
    },
    {
        "dado": "Vereadores no cargo hoje, projetos, votações e presença (câmaras com SAPL)",
        "orgao": "Câmaras municipais (sistema SAPL do Interlegis)",
        "fontes": ["sapl_camaras"],
        "url": "https://www.interlegis.leg.br/",
    },
    {
        "dado": "Deputados estaduais no cargo, projetos, votos e presença (assembleias com SAPL)",
        "orgao": "Assembleias legislativas de AC, AL, AM, PB, PI, RO, RR e TO (SAPL)",
        "fontes": ["sapl_assembleias"],
        "url": "https://www.interlegis.leg.br/",
    },
    {
        "dado": "Deputados estaduais de MG: no cargo, projetos e gastos do gabinete",
        "orgao": "Assembleia Legislativa de Minas Gerais (dados abertos)",
        "fontes": ["almg"],
        "url": "https://dadosabertos.almg.gov.br/",
    },
    {
        "dado": "Deputados estaduais de SP: no cargo, projetos e gastos do gabinete",
        "orgao": "Assembleia Legislativa de São Paulo (dados abertos)",
        "fontes": ["alesp"],
        "url": "https://www.al.sp.gov.br/dados-abertos/",
    },
    {
        "dado": "Deputados estaduais de PE: no cargo e projetos",
        "orgao": "Assembleia Legislativa de Pernambuco (dados abertos)",
        "fontes": ["alepe"],
        "url": "https://dadosabertos.alepe.pe.gov.br/",
    },
    {
        "dado": "Deputados distritais (DF): no cargo e projetos",
        "orgao": "Câmara Legislativa do Distrito Federal (API pública do processo legislativo)",
        "fontes": ["cldf"],
        "url": "https://dados.cl.df.gov.br/dataset/proposicoes",
    },
    {
        "dado": "Deputados estaduais de SC: no cargo e proposições",
        "orgao": "Assembleia Legislativa de Santa Catarina (páginas públicas do e-Legis)",
        "fontes": ["alesc"],
        "url": "https://portalelegis.alesc.sc.gov.br/",
    },
    {
        "dado": "Sites oficiais das prefeituras e câmaras (catálogo aberto)",
        "orgao": "Varredura do Panóptico nos domínios .gov.br e .leg.br",
        "fontes": ["canais_oficiais"],
        "url": "https://github.com/Gipsy7/panoptico/tree/dev/data",
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
