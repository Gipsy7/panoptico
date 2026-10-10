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
        "dado": "Finanças dos partidos: fundos, receitas, gastos e repasses a candidaturas",
        "orgao": "Tribunal Superior Eleitoral (prestação de contas anual dos partidos)",
        "fontes": ["tse_contas_partidarias", "tse_fefc_fp"],
        "url": "https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-partidarias-2024",
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
        "dado": "Vereadores no cargo hoje, projetos, votações e presença (câmaras com SAPL)",
        "orgao": "Câmaras municipais (sistema SAPL do Interlegis)",
        "fontes": ["sapl_camaras"],
        "url": "https://www.interlegis.leg.br/",
    },
    {
        "dado": "Vereadores no cargo hoje e proposições (câmaras no portal da Cittatec)",
        "orgao": "Câmaras de Pelotas, Erechim, São Borja, Ronda Alta e outras três (Cittatec)",
        "fontes": ["cittatec_camaras"],
        "url": "https://cmpelotas.cittatec.com.br/portal-legislativo/vereadores",
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
        "dado": "Deputados estaduais de SP: no cargo, projetos, gastos e votos nas comissões",
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
        "dado": "Deputados estaduais do RJ: no cargo (partido, foto e contato)",
        "orgao": "Assembleia Legislativa do Rio de Janeiro (páginas públicas do site)",
        "fontes": ["alerj"],
        "url": "https://www.alerj.rj.gov.br/Deputados/QuemSao",
    },
    {
        "dado": "Deputados estaduais do RS: no cargo, proposições, votos, presença e cota",
        "orgao": "Assembleia Legislativa do Rio Grande do Sul (portais da transparência)",
        "fontes": ["alrs"],
        "url": "https://transparencia.al.rs.gov.br/parlamentares",
    },
    {
        "dado": "Deputados estaduais da BA: no cargo, proposições e presença em plenário",
        "orgao": "Assembleia Legislativa da Bahia (dados abertos do processo legislativo)",
        "fontes": ["alba"],
        "url": "https://albalegis.nopapercloud.com.br/dados-abertos.aspx",
    },
    {
        "dado": "CPIs e CPMIs desde 2019: presidente, relator, membros e relatório final",
        "orgao": "Câmara dos Deputados, Senado Federal e Congresso Nacional",
        "fontes": ["cpis"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Deputados estaduais do ES: no cargo, proposições e presença em plenário",
        "orgao": "Assembleia Legislativa do Espírito Santo (dados abertos do processo legislativo)",
        "fontes": ["ales"],
        "url": "https://www3.al.es.gov.br/api/publico/parlamentar/",
    },
    {
        "dado": "Deputados estaduais do CE: no cargo (partido, foto e contato) e projetos",
        "orgao": "Assembleia Legislativa do Ceará (páginas públicas do site)",
        "fontes": ["alece"],
        "url": "https://www.al.ce.gov.br/deputados",
    },
    {
        "dado": "Deputados estaduais do PA: no cargo (partido e foto)",
        "orgao": "Assembleia Legislativa do Pará (página pública do portal)",
        "fontes": ["alepa"],
        "url": "https://www.alepa.pa.gov.br/Home/Page/Deputados",
    },
    {
        "dado": "Deputados estaduais de MT: no cargo (partido e foto)",
        "orgao": "Assembleia Legislativa de Mato Grosso (páginas públicas do site)",
        "fontes": ["almt"],
        "url": "https://www.al.mt.gov.br/parlamento/deputados",
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
