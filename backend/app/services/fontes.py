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
        "dado": "Votações nominais (Plenário e comissões) e orientação do Governo e dos partidos",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_votacoes", "senado_votacoes", "senado_votacoes_comissoes"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Projetos de lei e autores (inclui os projetos votados antes de 2023)",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": [
            "camara_proposicoes",
            "camara_proposicoes_votadas",
            "camara_autores",
            "senado_proposicoes",
        ],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Discursos em Plenário nos dias de votação (resumo publicado pela Casa e link)",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_discursos", "senado_discursos"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Pauta do Plenário nos próximos dias",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_pauta", "senado_pauta"],
        "url": "https://dadosabertos.camara.leg.br/",
    },
    {
        "dado": "Caminho dos projetos (tramitação) e relator",
        "orgao": "Câmara dos Deputados e Senado Federal",
        "fontes": ["camara_tramitacoes", "senado_tramitacoes"],
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
        "dado": "Indicações de emendas de relator-geral (RP9, 2022) com o parlamentar que pediu",
        "orgao": "Comissão Mista de Orçamento (Congresso Nacional)",
        "fontes": ["congresso_emendas_relator"],
        "url": "https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/"
        "Indicacoes-para-execucao-orcamentaria-em-RP9_LOA-2022",
    },
    {
        "dado": "O que aconteceu com o dinheiro das emendas: situação dos convênios e das "
        "transferências especiais, vigência e prestação de contas",
        "orgao": "CGU (Portal da Transparência) e Ministério da Gestão (TransfereGov)",
        "fontes": ["transferegov_convenios", "transferegov_especiais"],
        "url": "https://www.gov.br/transferegov/pt-br",
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
            "tse_resultado_2_turno",
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
        "dado": "Contas anuais dos governos estaduais (receita, despesa e áreas)",
        "orgao": "Tesouro Nacional (SICONFI)",
        "fontes": ["siconfi_contas_estados"],
        "url": "https://siconfi.tesouro.gov.br/",
    },
    {
        "dado": "Agenda de ministros e do vice-presidente: reuniões, viagens e presentes",
        "orgao": "Controladoria-Geral da União (e-Agendas)",
        "fontes": ["eagendas"],
        "url": "https://eagendas.cgu.gov.br/",
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
        "dado": "Vereadores no cargo hoje (câmaras com o modelo de site PHP de vereadores.php)",
        "orgao": "Câmaras de Amapá, Ferreira Gomes e Tartarugalzinho (AP), Fortim e Poranga (CE)",
        "fontes": ["portal_php_camaras"],
        "url": "https://amapa.ap.leg.br/vereadores",
    },
    {
        "dado": "Vereadores no cargo hoje (câmaras com o portal da Nucleogov / 7Focus)",
        "orgao": (
            "Câmaras de Pirenópolis e Campos Belos (GO), Cariri do Tocantins, Figueirópolis "
            "e Santa Rita do Tocantins (TO)"
        ),
        "fontes": ["nucleogov_camaras"],
        "url": "https://pirenopolis.go.leg.br/",
    },
    {
        "dado": (
            "Vereadores no cargo hoje (câmaras com o Portal Modelo do Interlegis "
            "e o site da AOS Software)"
        ),
        "orgao": "Câmaras de Imbuia (SC), Santana do Piauí e Queimada Nova (PI)",
        "fontes": ["portal_modelo_camaras", "aos_camaras"],
        "url": "https://www.imbuia.sc.leg.br/processo-legislativo/parlamentares",
    },
    {
        "dado": "Vereadores no cargo hoje (sites próprios das câmaras)",
        "orgao": "Câmaras de Palmas (TO), Teófilo Otoni e Frutal (MG)",
        "fontes": ["sistemas_camaras"],
        "url": "https://palmas.to.leg.br/",
    },
    {
        "dado": "Vereadores no cargo hoje (sites das câmaras de Senador Guiomard e Praia Grande)",
        "orgao": "Câmaras de Senador Guiomard (AC) e Praia Grande (SP)",
        "fontes": ["fornecedores_robin_camaras"],
        "url": "https://www.senadorguiomard.ac.leg.br/vereadores",
    },
    {
        "dado": "Vereadores no cargo hoje (sites próprios e de fornecedores das câmaras)",
        "orgao": (
            "Câmaras de Aracruz e Cachoeiro de Itapemirim (ES), Varjão de Minas (MG), "
            "Nortelândia (MT), Santa Maria do Cambucá (PE) e Alvorada (TO)"
        ),
        "fontes": ["fornecedores_alfred_camaras"],
        "url": "https://alvorada.to.leg.br/transparencia/vereador",
    },
    {
        "dado": "Vereadores no cargo hoje (sites próprios das câmaras)",
        "orgao": "Câmaras de Pimenta Bueno (RO), Perdões (MG) e Santa Cruz (PE)",
        "fontes": ["fornecedores_batgirl_camaras"],
        "url": "https://www.pimentabueno.ro.leg.br/",
    },
    {
        "dado": "Vereadores no cargo hoje (sites de fornecedores com muitas câmaras pequenas)",
        "orgao": (
            "Câmaras do Maranhão (webservicesistemas), Piauí (STS), Rio Grande do Sul "
            "(Cespro e iCamaras), Minas Gerais (Portal Fácil) e Paraná (Ingá Digital)"
        ),
        "fontes": ["fornecedores_cobertura_camaras"],
        "url": "https://cmbernardodomearim.ma.gov.br/vereadores",
    },
    {
        "dado": "Vereadores no cargo hoje (câmaras no Portal da Transparência da CR2)",
        "orgao": "Câmaras de Beruri (AM), Itamarandiba (MG), Benevides e São Miguel do Guamá (PA)",
        "fontes": ["cr2_camaras"],
        "url": "https://www.portalcr2.com.br/entidade/cm-beruri",
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
        "dado": "Deputados estaduais de SC: no cargo, proposições, presença e gastos do gabinete",
        "orgao": "Assembleia Legislativa de Santa Catarina (e-Legis e Portal da Transparência)",
        "fontes": ["alesc"],
        "url": "https://transparencia.alesc.sc.gov.br/gabinetes-parlamentares/dados-abertos",
    },
    {
        "dado": "Emendas de deputados estaduais de SC (impositivas): autor, cidade, quem recebeu "
        "e valores previsto, empenhado e pago",
        "orgao": "Controladoria-Geral do Estado de Santa Catarina (SC Transferências)",
        "fontes": ["sctransferencias_emendas"],
        "url": "https://consultas.sctransferencias.cge.sc.gov.br/pesquisa-detalhada/emendas",
    },
    {
        "dado": "Emendas de deputados estaduais de MG: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Secretaria de Estado de Governo de MG (Portal de Emendas Estaduais, dados "
        "abertos)",
        "fontes": ["segov_mg_emendas"],
        "url": "https://dados.mg.gov.br/dataset/portal_emendas_estaduais",
    },
    {
        "dado": "Emendas de deputados estaduais de BA: autor e valores previsto, empenhado e "
        "pago (sem cidade)",
        "orgao": "Secretaria da Fazenda da Bahia (FIPLAN, dados abertos)",
        "fontes": ["sefaz_ba_emendas"],
        "url": "https://dados.ba.gov.br/dataset/emendas-parlamentares",
    },
    {
        "dado": "Emendas de deputados estaduais de PE: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Secretaria de Planejamento de Pernambuco (dados abertos)",
        "fontes": ["seplag_pe_emendas"],
        "url": "https://dados.pe.gov.br/dataset/emendasparlamentaresestaduais",
    },
    {
        "dado": "Emendas de deputados estaduais de MA: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Portal da Transparência do Maranhão",
        "fontes": ["transparencia_ma_emendas"],
        "url": "https://www.transparencia.ma.gov.br/app/v2/emendasestaduais",
    },
    {
        "dado": "Emendas de deputados estaduais de ES: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Secretaria da Fazenda do Espírito Santo (dados abertos)",
        "fontes": ["sefaz_es_emendas"],
        "url": "https://dados.es.gov.br/dataset/portal-da-transparencia-emendas-parlamentares-do-estado",
    },
    {
        "dado": "Emendas de deputados estaduais de AL: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Portal da Transparência de Alagoas",
        "fontes": ["transparencia_al_emendas"],
        "url": "https://transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais",
    },
    {
        "dado": "Emendas de deputados estaduais de SE: autor, cidade, quem executa e valores "
        "indicado e pago",
        "orgao": "Portal da Transparência de Sergipe",
        "fontes": ["transparencia_se_emendas"],
        "url": "https://www.transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais",
    },
    {
        "dado": "Emendas de deputados estaduais de AC: autor, cidade, quem recebeu e valores "
        "previsto, empenhado e pago",
        "orgao": "Secretaria de Planejamento do Acre (Portal de Emendas Estaduais)",
        "fontes": ["seplan_ac_emendas"],
        "url": "https://seplan.ac.gov.br/gestao-de-recursos/convenios/emendas-parlamentares-estaduais/",
    },
    {
        "dado": "Emendas de deputados estaduais de GO (só 2023): autor, cidade, quem recebeu e "
        "valores previsto, empenhado e pago",
        "orgao": "Governo de Goiás (Portal de Dados Abertos)",
        "fontes": ["dadosabertos_go_emendas"],
        "url": "https://dadosabertos.go.gov.br/dataset/emendas-parlamentares",
    },
    {
        "dado": "Emendas de deputados estaduais da PB: autor e valores previsto, empenhado e "
        "pago (sem cidade)",
        "orgao": "Governo da Paraíba (API de dados abertos, CGE e Codata)",
        "fontes": ["dadospb_emendas"],
        "url": "https://transparencia.pb.gov.br/emendas-parlamentares",
    },
    {
        "dado": "Emendas de deputados distritais (DF): autor, ação e valores autorizado, "
        "empenhado e pago",
        "orgao": "Portal da Transparência do Distrito Federal",
        "fontes": ["transparencia_df_emendas"],
        "url": "https://www.transparencia.df.gov.br/#/despesas/emendas-parlamentares",
    },
    {
        "dado": "Deputados estaduais do PR: no cargo, presença em plenário e votos nominais",
        "orgao": "Assembleia Legislativa do Paraná (site e Portal da Transparência)",
        "fontes": ["alep"],
        "url": "https://transparencia.assembleia.pr.leg.br/servicos/dados-abertos",
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
        "dado": "Deputados estaduais do CE: no cargo, projetos, gastos e votações nominais",
        "orgao": "Assembleia Legislativa do Ceará (site e portal da transparência)",
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
        "dado": "Deputados estaduais do MA: no cargo (partido e foto) e projetos",
        "orgao": "Assembleia Legislativa do Maranhão (site e API pública do ALEMALEGIS)",
        "fontes": ["alema"],
        "url": "https://alemalegis.al.ma.leg.br/api/v1/public/legislative-matter/filter/access",
    },
    {
        "dado": "Deputados estaduais de MS: no cargo e gastos da cota (CEAP)",
        "orgao": "Assembleia Legislativa de Mato Grosso do Sul (site e portal da transparência)",
        "fontes": ["alems"],
        "url": "https://transparencia2.al.ms.gov.br/ceap",
    },
    {
        "dado": "Deputados estaduais do RN: no cargo, projetos, presença e votações nominais",
        "orgao": "Assembleia Legislativa do RN (site e API da transparência legislativa)",
        "fontes": ["alrn"],
        "url": "https://transparencialegislativa.al.rn.leg.br/",
    },
    {
        "dado": "Deputados estaduais de SE: no cargo, presença em plenário e projetos",
        "orgao": "Assembleia Legislativa de Sergipe (site e dados abertos do Processo Legislativo)",
        "fontes": ["alese"],
        "url": "https://aleselegis.al.se.leg.br/spl/",
    },
    {
        "dado": "Deputados estaduais do AP: no cargo (partido e foto) e projetos",
        "orgao": "Assembleia Legislativa do Amapá (site e portal do eLegis)",
        "fontes": ["alap"],
        "url": "https://elegis.al.ap.leg.br/portal/proposicoes",
    },
    {
        "dado": "Deputados estaduais de GO: no cargo, verba indenizatória, projetos e presença",
        "orgao": "Assembleia Legislativa de Goiás (portal, transparência e processo legislativo)",
        "fontes": ["alego"],
        "url": "https://transparencia.al.go.leg.br/dados-abertos",
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
        "dado": "Dinheiro federal por estado e cidade",
        "orgao": "Receita Federal, Tesouro Nacional, Portal da Transparência e IBGE",
        "fontes": [
            "receita_arrecadacao_uf",
            "tesouro_transferencias",
            "portal_transferencias",
            "ibge_populacao",
        ],
        "url": "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao",
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
