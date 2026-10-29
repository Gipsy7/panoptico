"""Os conjuntos públicos: o que sai, de onde vem, o que fica de fora.

Cada conjunto é uma consulta SQL que já devolve só o que pode ser publicado (os filtros
estão aqui, à vista) mais o dicionário das colunas. Nunca saem: CPF, título de eleitor, data
de nascimento, pessoa sem vínculo publicável (`app.services.pessoas.publicavel`), sugestões
não revisadas (diario_ato, dou_ato, cpi_indiciamento_sugestao) e casos em rascunho (que a
curadoria nem carrega no banco; aqui só saem casos com evento publicável).
"""

from dataclasses import dataclass, field

from app.models.pessoa import REGRAS_FORTES

TIPOS = {"texto", "inteiro", "decimal", "data", "datahora", "booleano", "json"}


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str
    descricao: str
    livre: bool = False  # texto livre: também some sequência de 11 dígitos (possível CPF)


@dataclass(frozen=True)
class Conjunto:
    nome: str
    titulo: str
    descricao: str
    orgao: str  # fonte oficial
    url: str
    fontes: tuple[str, ...]  # nomes em fonte_ingestao, para a data da última carga
    filtros: str  # o que fica de fora, em português
    sql: str
    colunas: tuple[Coluna, ...] = field(default_factory=tuple)


def _c(nome: str, tipo: str, descricao: str, livre: bool = False) -> Coluna:
    assert tipo in TIPOS, tipo
    return Coluna(nome, tipo, descricao, livre)


_REGRAS = ", ".join(f"'{r}'" for r in sorted(REGRAS_FORTES))
# Mesma regra de app.services.pessoas.publicavel(), em SQL: vínculo forte ou revisado.
PUBLICAVEL = f"(v.regra IN ({_REGRAS}) OR v.revisado IS TRUE)"

# Vínculos publicáveis de agentes públicos: parlamentar, vereador/deputado estadual ou
# candidatura eleita. Pessoa que só tem vínculo fraco (não revisado) não aparece em lugar nenhum.
VP = f"""vp AS (
  SELECT v.id, v.pessoa_id, v.fonte, v.id_externo, v.regra, v.revisado
  FROM pessoa_vinculo v
  WHERE {PUBLICAVEL}
    AND (v.fonte IN ('parlamentar', 'mandato_local')
         OR (v.fonte = 'candidatura' AND EXISTS (
               SELECT 1 FROM candidatura c
               WHERE c.ano_eleicao::text || ':' || c.sq_candidato = v.id_externo
                 AND c.situacao_turno LIKE 'ELEITO%')))
)"""

ELEITA = "c.situacao_turno LIKE 'ELEITO%'"


# Documento de fornecedor: só CNPJ (14 dígitos) sai. Vazio fica vazio; qualquer outra coisa
# (CPF, CPF mascarado, documento estrangeiro) é tratada como pessoa física e some, com o nome.
def _doc(col: str) -> str:
    return f"regexp_replace(coalesce({col}, ''), '\\D', '', 'g')"


def _doc_pf(col: str) -> str:
    d = _doc(col)
    return f"({d} <> '' AND length({d}) <> 14)"


# Eventos publicáveis (reaproveitado por processos e casos).
EVENTO_PUBLICAVEL = "evento e JOIN vp ON vp.id = e.vinculo_id AND vp.pessoa_id = e.pessoa_id"

CONJUNTOS: tuple[Conjunto, ...] = (
    Conjunto(
        nome="parlamentares_federais",
        titulo="Deputados federais e senadores",
        descricao="Parlamentares federais registrados no acervo (em exercício ou já listados).",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_deputados", "senado_senadores"),
        filtros="Sem CPF, e-mail e telefone.",
        sql="""SELECT id, casa, id_externo, nome_parlamentar, nome_civil, partido, uf,
                      em_exercicio, em_exercicio_desde, pagina_url, foto_url, fonte_url,
                      atualizado_em
               FROM parlamentar ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados (chave das despesas)."),
            _c("casa", "texto", "camara ou senado."),
            _c("id_externo", "texto", "Código do parlamentar na Casa."),
            _c("nome_parlamentar", "texto", "Nome parlamentar."),
            _c("nome_civil", "texto", "Nome civil, quando a Casa informa."),
            _c("partido", "texto", "Sigla do partido atual."),
            _c("uf", "texto", "Estado que representa."),
            _c("em_exercicio", "booleano", "Se está em exercício na data da carga."),
            _c("em_exercicio_desde", "data", "Início do período atual de exercício."),
            _c("pagina_url", "texto", "Página oficial do parlamentar."),
            _c("foto_url", "texto", "Foto oficial."),
            _c("fonte_url", "texto", "Endereço do registro na fonte."),
            _c("atualizado_em", "datahora", "Quando o registro foi atualizado no acervo."),
        ),
    ),
    Conjunto(
        nome="municipios",
        titulo="Municípios",
        descricao="Tabela de municípios do IBGE, para ligar os códigos dos outros conjuntos.",
        orgao="IBGE",
        url="https://servicodados.ibge.gov.br/api/docs/localidades",
        fontes=("ibge_municipios",),
        filtros="Nenhum.",
        sql="SELECT ibge, nome, uf FROM municipio ORDER BY ibge",
        colunas=(
            _c("ibge", "texto", "Código IBGE de 7 dígitos."),
            _c("nome", "texto", "Nome do município."),
            _c("uf", "texto", "Sigla do estado."),
        ),
    ),
    Conjunto(
        nome="mandatos_locais",
        titulo="Vereadores e deputados estaduais",
        descricao="Quem está no cargo numa câmara municipal ou assembleia, como a própria casa "
        "publica (SAPL e portais das assembleias).",
        orgao="Câmaras municipais e assembleias legislativas",
        url="https://www.interlegis.leg.br/ (SAPL) e os portais de cada casa; ver sapl_url",
        fontes=("sapl_camaras", "sapl_assembleias"),
        filtros="Sem e-mail e telefone. A ligação à candidatura (candidatura_id) só vai quando "
        "o vínculo da pessoa é forte ou foi revisado.",
        sql=f"""SELECT m.id, m.casa, m.uf, m.municipio_ibge, m.id_externo, m.nome, m.nome_completo,
                       m.partido, m.titular, m.em_exercicio, m.inicio, m.fim,
                       m.proposicoes_por_tipo, m.sessoes, m.presencas,
                       CASE WHEN EXISTS (
                         SELECT 1 FROM pessoa_vinculo v
                         WHERE v.fonte = 'mandato_local'
                           AND v.id_externo = m.casa || ':' || m.uf || ':'
                               || coalesce(m.municipio_ibge, '') || ':' || m.id_externo
                           AND {PUBLICAVEL})
                       THEN m.candidatura_id END AS candidatura_id,
                       m.sapl_url, m.foto_url
                FROM mandato_local m ORDER BY m.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "camara (municipal) ou assembleia."),
            _c("uf", "texto", "Estado."),
            _c("municipio_ibge", "texto", "Código IBGE do município (vazio nas assembleias)."),
            _c("id_externo", "texto", "Código do parlamentar na casa."),
            _c("nome", "texto", "Nome parlamentar."),
            _c("nome_completo", "texto", "Nome completo, quando a casa informa."),
            _c("partido", "texto", "Sigla do partido atual."),
            _c("titular", "booleano", "Titular (verdadeiro) ou suplente."),
            _c("em_exercicio", "booleano", "Se está em exercício."),
            _c("inicio", "data", "Início do mandato."),
            _c("fim", "data", "Fim do mandato, quando informado."),
            _c("proposicoes_por_tipo", "json", "Contagem de proposições como autor, por tipo."),
            _c("sessoes", "inteiro", "Sessões plenárias com presença registrada no período."),
            _c("presencas", "inteiro", "Sessões em que estava presente."),
            _c("candidatura_id", "inteiro", "Candidatura eleita ligada (candidaturas_eleitas.id)."),
            _c("sapl_url", "texto", "Página do parlamentar na casa."),
            _c("foto_url", "texto", "Foto oficial."),
        ),
    ),
    Conjunto(
        nome="candidaturas_eleitas",
        titulo="Candidaturas eleitas",
        descricao="Candidaturas com resultado ELEITO (inclui eleito por QP e por média) nas "
        "eleições guardadas no acervo.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_candidaturas",),
        filtros="Só eleitos. Sem CPF, título de eleitor, data de nascimento, cor ou raça e "
        "estado civil.",
        sql=f"""SELECT c.id, c.ano_eleicao, c.sq_candidato, c.cargo, c.uf, c.unidade,
                       c.municipio_ibge, c.nome, c.nome_urna, c.partido, c.numero,
                       c.situacao_turno, c.situacao_candidatura, c.data_eleicao, c.genero,
                       c.grau_instrucao, c.ocupacao, c.votos, c.chapa_titular_id,
                       c.parlamentar_id
                FROM candidatura c WHERE {ELEITA} ORDER BY c.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("ano_eleicao", "inteiro", "Ano da eleição."),
            _c("sq_candidato", "texto", "Sequencial da candidatura no TSE."),
            _c("cargo", "texto", "Cargo disputado."),
            _c("uf", "texto", "Estado (BR para presidente)."),
            _c("unidade", "texto", "Estado ou município da disputa."),
            _c("municipio_ibge", "texto", "Código IBGE do município, nas eleições municipais."),
            _c("nome", "texto", "Nome civil registrado."),
            _c("nome_urna", "texto", "Nome de urna."),
            _c("partido", "texto", "Sigla do partido."),
            _c("numero", "texto", "Número de urna."),
            _c("situacao_turno", "texto", "Resultado (ELEITO, ELEITO POR QP, ELEITO POR MEDIA)."),
            _c("situacao_candidatura", "texto", "Situação do registro (APTO etc.)."),
            _c("data_eleicao", "data", "Data do turno que definiu o resultado."),
            _c("genero", "texto", "Gênero declarado."),
            _c("grau_instrucao", "texto", "Grau de instrução declarado."),
            _c("ocupacao", "texto", "Ocupação declarada."),
            _c("votos", "inteiro", "Votos nominais válidos no turno do resultado."),
            _c("chapa_titular_id", "inteiro", "Para vice: candidaturas_eleitas.id do titular."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id, quando ligado por CPF."),
        ),
    ),
    Conjunto(
        nome="bens_declarados",
        titulo="Bens declarados pelos eleitos",
        descricao="Bens declarados ao TSE na candidatura, com o valor como declarado.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_bens",),
        filtros="Só candidaturas eleitas.",
        sql=f"""SELECT b.candidatura_id, b.ordem, b.tipo, b.descricao, b.valor
                FROM bem_declarado b JOIN candidatura c ON c.id = b.candidatura_id
                WHERE {ELEITA} ORDER BY b.candidatura_id, b.ordem""",
        colunas=(
            _c("candidatura_id", "inteiro", "candidaturas_eleitas.id."),
            _c("ordem", "inteiro", "Ordem do bem na declaração."),
            _c("tipo", "texto", "Tipo do bem."),
            _c("descricao", "texto", "Descrição declarada.", livre=True),
            _c("valor", "decimal", "Valor em reais, como declarado (sem correção)."),
        ),
    ),
    Conjunto(
        nome="campanhas_resumo",
        titulo="Totais da campanha dos eleitos",
        descricao="Totais da prestação de contas de campanha. Sem doadores.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_campanha",),
        filtros="Só candidaturas eleitas; só totais (sem doador ou fornecedor).",
        sql=f"""SELECT r.candidatura_id, r.receitas_total, r.receitas_por_origem,
                       r.despesas_total, r.despesas_por_tipo, r.numero_doadores
                FROM campanha_resumo r JOIN candidatura c ON c.id = r.candidatura_id
                WHERE {ELEITA} ORDER BY r.candidatura_id""",
        colunas=(
            _c("candidatura_id", "inteiro", "candidaturas_eleitas.id."),
            _c("receitas_total", "decimal", "Total de receitas da campanha, em reais."),
            _c("receitas_por_origem", "json", "Receitas por origem (fundo eleitoral etc.)."),
            _c("despesas_total", "decimal", "Total de despesas da campanha, em reais."),
            _c("despesas_por_tipo", "json", "Despesas por tipo."),
            _c("numero_doadores", "inteiro", "Quantidade de doadores (sem nomes)."),
        ),
    ),
    Conjunto(
        nome="pessoas_publicas",
        titulo="Pessoas públicas com vínculo publicável",
        descricao="Quem aparece nos eventos e nos vínculos: parlamentares, vereadores, "
        "deputados estaduais e eleitos, com ao menos um vínculo forte ou revisado.",
        orgao="Panóptico (junção das fontes oficiais)",
        url="https://github.com/Gipsy7/Panoptico",
        fontes=("pessoas",),
        filtros="Só pessoa com vínculo publicável de agente público. Sem CPF, título e data de "
        "nascimento. Pessoa privada ou só com vínculo fraco não sai.",
        sql=f"""WITH {VP}
                SELECT p.id, p.nome FROM pessoa p
                WHERE EXISTS (SELECT 1 FROM vp WHERE vp.pessoa_id = p.id) ORDER BY p.id""",
        colunas=(
            _c("id", "inteiro", "Identificador da pessoa neste conjunto de dados."),
            _c("nome", "texto", "Nome."),
        ),
    ),
    Conjunto(
        nome="vinculos_publicaveis",
        titulo="Vínculos entre pessoa e registros das fontes",
        descricao="Liga cada pessoa aos registros de parlamentar, mandato local e candidatura "
        "eleita, com a regra que fez a ligação.",
        orgao="Panóptico (junção das fontes oficiais)",
        url="https://github.com/Gipsy7/Panoptico",
        fontes=("pessoas",),
        filtros="Só vínculos fortes ou revisados à mão (`publicavel()`).",
        sql=f"""WITH {VP}
                SELECT vp.pessoa_id, vp.fonte, vp.id_externo, vp.regra, vp.revisado
                FROM vp ORDER BY vp.pessoa_id, vp.fonte, vp.id_externo""",
        colunas=(
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("fonte", "texto", "parlamentar, mandato_local ou candidatura."),
            _c(
                "id_externo",
                "texto",
                "Chave do registro: casa:id_externo (parlamentar), "
                "casa:uf:ibge:id_externo (mandato_local) ou ano_eleicao:sq_candidato.",
            ),
            _c("regra", "texto", "Regra da ligação (origem, cpf, titulo, nome_exato_casa...)."),
            _c("revisado", "booleano", "Se uma pessoa conferiu a ligação."),
        ),
    ),
    Conjunto(
        nome="eventos",
        titulo="Linha do tempo (eventos publicáveis)",
        descricao="Fatos datados da vida pública, cada um com a fonte oficial: sanções, "
        "cassações, condenações, processos, participações em casos documentados.",
        orgao="Vários órgãos oficiais (TSE, TCU, CGU, tribunais, Congresso); ver fonte_url",
        url="https://github.com/Gipsy7/Panoptico",
        fontes=(
            "tse_cassacoes",
            "tcu_condenacoes",
            "cgu_sancoes",
            "camara_etica",
            "senado_etica",
            "curadoria",
            "cnj_datajud",
        ),
        filtros="Só eventos cujo vínculo é forte ou revisado. Sem as sugestões de atos de "
        "diários oficiais e do DOU e de indiciamento de CPI (diario_ato, dou_ato, "
        "cpi_indiciamento_sugestao), que nunca são publicadas sem revisão.",
        sql=f"""WITH {VP}
                SELECT e.id, e.pessoa_id, e.data, e.tipo, e.descricao, e.orgao,
                       e.numero_processo, e.situacao, e.fonte, e.fonte_url, e.caso_slug,
                       vp.regra AS vinculo_regra
                FROM {EVENTO_PUBLICAVEL}
                ORDER BY e.id""",
        colunas=(
            _c("id", "inteiro", "Identificador do evento neste conjunto de dados."),
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("data", "data", "Data do fato."),
            _c("tipo", "texto", "Tipo (cassacao, sancao, processo, condenacao...)."),
            _c("descricao", "texto", "Descrição factual do evento.", livre=True),
            _c("orgao", "texto", "Órgão responsável."),
            _c("numero_processo", "texto", "Número do processo, quando há."),
            _c("situacao", "texto", "Situação informada pela fonte."),
            _c("fonte", "texto", "Nome da carga de origem."),
            _c("fonte_url", "texto", "Documento ou página oficial do fato."),
            _c("caso_slug", "texto", "casos.slug, quando o evento pertence a um caso."),
            _c("vinculo_regra", "texto", "Regra que ligou o evento à pessoa."),
        ),
    ),
    Conjunto(
        nome="processos",
        titulo="Situação dos processos citados nos eventos",
        descricao="Situação, no DataJud do CNJ, de processos judiciais citados em eventos.",
        orgao="Conselho Nacional de Justiça (DataJud)",
        url="https://datajud-wiki.cnj.jus.br/",
        fontes=("cnj_datajud",),
        filtros="Só processos citados em eventos publicáveis. Processo sigiloso sai só com "
        "número e tribunal.",
        sql=f"""WITH {VP}
                SELECT p.numero, p.tribunal,
                       CASE WHEN NOT p.sigiloso THEN p.classe END AS classe,
                       CASE WHEN NOT p.sigiloso THEN p.orgao_julgador END AS orgao_julgador,
                       CASE WHEN NOT p.sigiloso THEN p.data_ajuizamento END AS data_ajuizamento,
                       CASE WHEN NOT p.sigiloso THEN p.ultimo_andamento END AS ultimo_andamento,
                       CASE WHEN NOT p.sigiloso THEN p.data_ultimo_andamento END
                         AS data_ultimo_andamento,
                       p.sigiloso, p.encontrado, p.consultado_em
                FROM processo p
                WHERE p.numero IN (SELECT e.numero_processo FROM {EVENTO_PUBLICAVEL}
                                   WHERE e.numero_processo IS NOT NULL)
                ORDER BY p.numero""",
        colunas=(
            _c("numero", "texto", "Número único do processo (padrão CNJ)."),
            _c("tribunal", "texto", "Tribunal."),
            _c("classe", "texto", "Classe processual."),
            _c("orgao_julgador", "texto", "Órgão julgador."),
            _c("data_ajuizamento", "data", "Data do ajuizamento."),
            _c("ultimo_andamento", "texto", "Último andamento registrado."),
            _c("data_ultimo_andamento", "data", "Data do último andamento."),
            _c("sigiloso", "booleano", "Se o processo corre sob sigilo."),
            _c("encontrado", "booleano", "Se foi encontrado no DataJud."),
            _c("consultado_em", "data", "Dia da consulta ao DataJud."),
        ),
    ),
    Conjunto(
        nome="casos",
        titulo="Casos documentados",
        descricao="Casos (escândalos) montados só com documentos oficiais.",
        orgao="Documentos oficiais citados em cada caso; ver casos_documentos.url",
        url="https://github.com/Gipsy7/Panoptico",
        fontes=("curadoria",),
        filtros="Só casos com ao menos um evento publicável. Rascunhos não entram no banco.",
        sql=f"""WITH {VP}
                SELECT c.slug, c.nome, c.periodo, c.resumo, c.conferido_em FROM caso c
                WHERE c.slug IN (SELECT e.caso_slug FROM {EVENTO_PUBLICAVEL}
                                 WHERE e.caso_slug IS NOT NULL)
                ORDER BY c.slug""",
        colunas=(
            _c("slug", "texto", "Identificador do caso."),
            _c("nome", "texto", "Nome do caso."),
            _c("periodo", "texto", "Período."),
            _c("resumo", "texto", "Resumo factual.", livre=True),
            _c("conferido_em", "data", "Dia da última conferência dos documentos."),
        ),
    ),
    Conjunto(
        nome="casos_documentos",
        titulo="Documentos oficiais dos casos",
        descricao="Cada documento oficial que sustenta um caso, com o endereço.",
        orgao="Órgãos de origem de cada documento",
        url="https://github.com/Gipsy7/Panoptico",
        fontes=("curadoria",),
        filtros="Só documentos de casos publicáveis (ver casos).",
        sql=f"""WITH {VP}
                SELECT d.caso_slug, d.codigo, d.tipo, d.orgao, d.numero, d.data, d.url, d.resumo
                FROM caso_documento d
                WHERE d.caso_slug IN (SELECT e.caso_slug FROM {EVENTO_PUBLICAVEL}
                                      WHERE e.caso_slug IS NOT NULL)
                ORDER BY d.caso_slug, d.codigo""",
        colunas=(
            _c("caso_slug", "texto", "casos.slug."),
            _c("codigo", "texto", "Código do documento no caso."),
            _c("tipo", "texto", "Tipo (denúncia, acórdão, relatório de CPI...)."),
            _c("orgao", "texto", "Órgão que produziu o documento."),
            _c("numero", "texto", "Número do documento."),
            _c("data", "data", "Data do documento."),
            _c("url", "texto", "Endereço do documento oficial."),
            _c("resumo", "texto", "Resumo factual.", livre=True),
        ),
    ),
    Conjunto(
        nome="cpis",
        titulo="CPIs e CPMIs",
        descricao="Comissões parlamentares de inquérito criadas desde 2019.",
        orgao="Câmara dos Deputados, Senado Federal e Congresso Nacional",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("cpis",),
        filtros="Sem as sugestões de indiciamento extraídas dos relatórios.",
        sql="""SELECT id, casa, id_externo, tipo, sigla, nome, objeto, data_criacao,
                      data_instalacao, data_fim, situacao, relatorio_url, relatorio_rotulo,
                      fonte_url
               FROM cpi ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "camara, senado ou congresso."),
            _c("id_externo", "texto", "Código do órgão na casa."),
            _c("tipo", "texto", "CPI ou CPMI."),
            _c("sigla", "texto", "Sigla."),
            _c("nome", "texto", "Nome."),
            _c("objeto", "texto", "Finalidade, no texto da casa.", livre=True),
            _c("data_criacao", "data", "Data de criação."),
            _c("data_instalacao", "data", "Data de instalação."),
            _c("data_fim", "data", "Fim (ou último prazo final registrado)."),
            _c("situacao", "texto", "Situação."),
            _c("relatorio_url", "texto", "Relatório final, quando há."),
            _c("relatorio_rotulo", "texto", "Rótulo do relatório."),
            _c("fonte_url", "texto", "Página oficial."),
        ),
    ),
    Conjunto(
        nome="cpis_participacoes",
        titulo="Membros das CPIs",
        descricao="Parlamentares membros de cada CPI/CPMI, com o cargo na comissão.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("cpis",),
        filtros="Sem a ligação a `pessoa`; o parlamentar é identificado pelo código oficial.",
        sql="""SELECT cpi_id, casa_parlamentar, id_parlamentar, nome, partido, uf, cargo,
                      data_inicio, data_fim
               FROM cpi_participacao ORDER BY cpi_id, id""",
        colunas=(
            _c("cpi_id", "inteiro", "cpis.id."),
            _c("casa_parlamentar", "texto", "camara ou senado."),
            _c("id_parlamentar", "texto", "Código do parlamentar na casa."),
            _c("nome", "texto", "Nome."),
            _c("partido", "texto", "Partido."),
            _c("uf", "texto", "Estado."),
            _c("cargo", "texto", "Presidente, Vice-presidente, Relator, Titular ou Suplente."),
            _c("data_inicio", "data", "Início na comissão."),
            _c("data_fim", "data", "Fim na comissão."),
        ),
    ),
    Conjunto(
        nome="despesas_cota",
        titulo="Cota parlamentar (deputados e senadores)",
        descricao="Despesas reembolsadas pela cota parlamentar (CEAP e CEAPS), uma linha por "
        "documento.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://www.camara.leg.br/transparencia/gastos-parlamentares",
        fontes=("camara_despesas", "senado_despesas"),
        filtros="Fornecedor sem CNPJ válido (pessoa física, CPF mascarado) sai sem nome e sem "
        "documento, com tipo_fornecedor = pessoa_fisica.",
        sql=f"""SELECT d.id, d.parlamentar_id, d.casa, d.ano, d.mes, d.categoria,
                       CASE WHEN {_doc_pf("d.cnpj_cpf")} THEN NULL ELSE d.fornecedor END
                         AS fornecedor,
                       CASE WHEN length({_doc("d.cnpj_cpf")}) = 14
                            THEN {_doc("d.cnpj_cpf")} END AS fornecedor_cnpj,
                       CASE WHEN {_doc_pf("d.cnpj_cpf")} THEN 'pessoa_fisica'
                            WHEN {_doc("d.cnpj_cpf")} = '' THEN 'sem_documento'
                            ELSE 'empresa' END AS tipo_fornecedor,
                       d.valor, d.data, d.url_documento, d.id_externo
                FROM despesa d ORDER BY d.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id."),
            _c("casa", "texto", "camara ou senado."),
            _c("ano", "inteiro", "Ano da despesa."),
            _c("mes", "inteiro", "Mês da despesa."),
            _c("categoria", "texto", "Categoria da despesa."),
            _c("fornecedor", "texto", "Nome do fornecedor (vazio para pessoa física).", True),
            _c("fornecedor_cnpj", "texto", "CNPJ do fornecedor (14 dígitos)."),
            _c("tipo_fornecedor", "texto", "empresa, pessoa_fisica ou sem_documento."),
            _c("valor", "decimal", "Valor reembolsado, em reais."),
            _c("data", "data", "Data do documento fiscal."),
            _c("url_documento", "texto", "Endereço do documento na fonte."),
            _c("id_externo", "texto", "Código do documento na fonte."),
        ),
    ),
    Conjunto(
        nome="gastos_locais",
        titulo="Verba indenizatória de deputados estaduais",
        descricao="Gastos de gabinete reembolsados, por mês e categoria, onde a assembleia "
        "publica (hoje, a ALMG).",
        orgao="Assembleias legislativas",
        url="https://dadosabertos.almg.gov.br/",
        fontes=("almg",),
        filtros="Só totais por mês e categoria; sem fornecedores.",
        sql="""SELECT mandato_id, ano, mes, categoria, valor FROM gasto_local
               ORDER BY mandato_id, ano, mes, categoria""",
        colunas=(
            _c("mandato_id", "inteiro", "mandatos_locais.id."),
            _c("ano", "inteiro", "Ano."),
            _c("mes", "inteiro", "Mês."),
            _c("categoria", "texto", "Categoria."),
            _c("valor", "decimal", "Valor, em reais."),
        ),
    ),
    Conjunto(
        nome="partidos_contas_somas",
        titulo="Contas anuais dos partidos (somas)",
        descricao="Prestação de contas anual dos partidos, somada por esfera, UF, fonte do "
        "recurso e categoria. A coluna natureza separa dinheiro que entra ou sai do que só "
        "muda de mãos dentro do partido.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_contas_partidarias",),
        filtros="Só totais; sem doador, fornecedor ou CPF.",
        sql="""SELECT ano, tipo, partido, esfera, uf, fonte_recurso, natureza, categoria,
                      valor, lancamentos
               FROM partido_conta_soma
               ORDER BY ano, tipo, partido, esfera, uf, fonte_recurso, natureza, categoria""",
        colunas=(
            _c("ano", "inteiro", "Exercício da prestação de contas."),
            _c("tipo", "texto", "receita ou despesa."),
            _c("partido", "texto", "Sigla do partido."),
            _c("esfera", "texto", "Nacional, Estadual, Distrital ou Municipal."),
            _c("uf", "texto", "Estado (vazio na esfera nacional)."),
            _c("fonte_recurso", "texto", "Fonte do recurso."),
            _c("natureza", "texto", "Natureza do lançamento (gasto, transferência...)."),
            _c("categoria", "texto", "Categoria."),
            _c("valor", "decimal", "Soma, em reais."),
            _c("lancamentos", "inteiro", "Quantidade de lançamentos somados."),
        ),
    ),
    Conjunto(
        nome="partidos_cotas_mensais",
        titulo="Fundo Partidário e FEFC recebidos por mês",
        descricao="Cotas do Fundo Partidário e do Fundo Especial de Financiamento de Campanha "
        "recebidas pelo diretório nacional, mês a mês.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_contas_partidarias",),
        filtros="Nenhum além do recorte da fonte.",
        sql="SELECT ano, mes, partido, fundo, valor FROM partido_cota_mensal "
        "ORDER BY ano, mes, partido, fundo",
        colunas=(
            _c("ano", "inteiro", "Exercício."),
            _c("mes", "data", "Primeiro dia do mês do recebimento."),
            _c("partido", "texto", "Sigla do partido."),
            _c("fundo", "texto", "Fundo Partidário ou FEFC."),
            _c("valor", "decimal", "Valor, em reais."),
        ),
    ),
    Conjunto(
        nome="partidos_fefc_fp",
        titulo="Distribuição do FEFC e do Fundo Partidário a candidaturas",
        descricao="Valores repassados a candidaturas por gênero e por cor ou raça, por eleição, "
        "partido e esfera. valor_partido repete em cada linha do partido: não some entre linhas.",
        orgao="Tribunal Superior Eleitoral (TSE)",
        url="https://dadosabertos.tse.jus.br/",
        fontes=("tse_fefc_fp",),
        filtros="Só totais por grupo.",
        sql="""SELECT ano, fundo, partido, esfera, genero, cor_raca, candidatos, valor_recebido,
                      valor_minimo_cota, valor_partido
               FROM partido_fefc_fp ORDER BY ano, fundo, partido, esfera, genero, cor_raca""",
        colunas=(
            _c("ano", "inteiro", "Ano da eleição."),
            _c("fundo", "texto", "FEFC ou FP."),
            _c("partido", "texto", "Sigla do partido."),
            _c("esfera", "texto", "Esfera partidária."),
            _c("genero", "texto", "Gênero."),
            _c("cor_raca", "texto", "Cor ou raça (vazio = geral)."),
            _c("candidatos", "inteiro", "Candidaturas no grupo."),
            _c("valor_recebido", "decimal", "Valor recebido pelo grupo, em reais."),
            _c("valor_minimo_cota", "decimal", "Valor mínimo da cota, quando há."),
            _c("valor_partido", "decimal", "Total do partido (repete em cada linha)."),
        ),
    ),
    Conjunto(
        nome="pncp_anual",
        titulo="Contratos do PNCP: soma anual por município e fornecedor",
        descricao="Soma, por município e fornecedor (CNPJ), dos contratos publicados no PNCP "
        "por órgãos municipais, sem alienações. Só os maiores fornecedores de cada município "
        "e só o ano atual e o anterior. Contratos com valor que parece incorreto (acima da "
        "despesa paga anual do município ou de R$ 50 bilhões) ficam fora da soma.",
        orgao="Portal Nacional de Contratações Públicas (PNCP)",
        url="https://pncp.gov.br/",
        fontes=("pncp_contratos",),
        filtros="Só fornecedor com CNPJ de 14 dígitos; pessoa física e estrangeiro não entram. "
        "Sequências de 11 dígitos nos nomes são removidas.",
        sql="""SELECT ano, municipio_ibge, fornecedor_cnpj, fornecedor_nome, quantidade,
                      valor_global
               FROM pncp_anual WHERE length(fornecedor_cnpj) = 14
               ORDER BY ano, municipio_ibge, fornecedor_cnpj""",
        colunas=(
            _c("ano", "inteiro", "Ano de publicação."),
            _c("municipio_ibge", "texto", "Código IBGE do município do órgão."),
            _c("fornecedor_cnpj", "texto", "CNPJ do fornecedor."),
            _c("fornecedor_nome", "texto", "Nome do fornecedor.", livre=True),
            _c("quantidade", "inteiro", "Contratos somados."),
            _c("valor_global", "decimal", "Soma do valor global, em reais."),
        ),
    ),
    Conjunto(
        nome="pncp_contratos",
        titulo="Contratos do PNCP de empresas do conjunto-alvo",
        descricao="Contratos inteiros do PNCP cujo fornecedor é empresa de sócio que o "
        "acervo acompanha ou empresa sancionada pela CGU.",
        orgao="Portal Nacional de Contratações Públicas (PNCP)",
        url="https://pncp.gov.br/",
        fontes=("pncp_contratos",),
        filtros="Só fornecedor com CNPJ de 14 dígitos; sem a identificação do sócio. "
        "Sequências de 11 dígitos nos textos são removidas.",
        sql="""SELECT numero_controle, orgao_cnpj, orgao_nome, esfera, uf, municipio_ibge,
                      municipio_nome, fornecedor_cnpj, fornecedor_nome, tipo_contrato,
                      categoria, receita, objeto, valor_inicial, valor_global, valor_acumulado,
                      data_assinatura, vigencia_inicio, vigencia_fim, publicado_em,
                      compra_pncp, processo, valor_suspeito
               FROM pncp_contrato WHERE length(fornecedor_cnpj) = 14
               ORDER BY numero_controle""",
        colunas=(
            _c("numero_controle", "texto", "Número de controle PNCP do contrato."),
            _c("orgao_cnpj", "texto", "CNPJ do órgão contratante."),
            _c("orgao_nome", "texto", "Nome do órgão."),
            _c("esfera", "texto", "F federal, E estadual, M municipal."),
            _c("uf", "texto", "Estado."),
            _c("municipio_ibge", "texto", "Código IBGE do município."),
            _c("municipio_nome", "texto", "Nome do município."),
            _c("fornecedor_cnpj", "texto", "CNPJ do fornecedor."),
            _c("fornecedor_nome", "texto", "Nome do fornecedor.", livre=True),
            _c("tipo_contrato", "texto", "Tipo de contrato."),
            _c("categoria", "texto", "Categoria do processo."),
            _c("receita", "booleano", "Se é receita (alienação)."),
            _c("objeto", "texto", "Objeto do contrato.", livre=True),
            _c("valor_inicial", "decimal", "Valor inicial, em reais."),
            _c("valor_global", "decimal", "Valor global, em reais."),
            _c("valor_acumulado", "decimal", "Valor acumulado, em reais."),
            _c("data_assinatura", "data", "Data de assinatura."),
            _c("vigencia_inicio", "data", "Início da vigência."),
            _c("vigencia_fim", "data", "Fim da vigência."),
            _c("publicado_em", "data", "Data de publicação no PNCP."),
            _c("compra_pncp", "texto", "Compra de origem no PNCP."),
            _c("processo", "texto", "Número do processo administrativo.", livre=True),
            _c(
                "valor_suspeito",
                "booleano",
                "Se o valor informado ao PNCP parece incorreto (passa da despesa paga anual do "
                "município ou de R$ 50 bilhões); o valor original não foi alterado.",
            ),  # fmt: skip
        ),
    ),
    Conjunto(
        nome="despesas_fornecedor_tce",
        titulo="Para quem a prefeitura pagou (TCE-SP e TCE-RS)",
        descricao="Total pago no ano por fornecedor, por município e órgão (prefeitura, "
        "câmara, outros): os 25 maiores de cada órgão, 'Demais fornecedores', pessoas físicas "
        "somadas sem nome e a folha numa linha própria.",
        orgao="Tribunais de Contas dos Estados de São Paulo e do Rio Grande do Sul",
        url="https://transparencia.tce.sp.gov.br/ e https://dados.tce.rs.gov.br/",
        fontes=("tce_sp", "tce_rs"),
        filtros="Só CNPJ de 14 dígitos; qualquer outro documento sai sem nome e sem número.",
        sql=f"""SELECT municipio_ibge, ano, orgao,
                       CASE WHEN {_doc_pf("documento")} THEN NULL ELSE fornecedor END
                         AS fornecedor,
                       CASE WHEN length({_doc("documento")}) = 14
                            THEN {_doc("documento")} END AS fornecedor_cnpj,
                       valor_pago, pagamentos, fonte
                FROM despesa_fornecedor ORDER BY fonte, ano, municipio_ibge, orgao, id""",
        colunas=(
            _c("municipio_ibge", "texto", "Código IBGE do município."),
            _c("ano", "inteiro", "Ano dos pagamentos."),
            _c("orgao", "texto", "prefeitura, camara ou outros."),
            _c(
                "fornecedor", "texto", "Fornecedor ou linha agregada ('Demais fornecedores').", True
            ),
            _c("fornecedor_cnpj", "texto", "CNPJ do fornecedor (vazio nas linhas agregadas)."),
            _c("valor_pago", "decimal", "Total pago no ano, em reais."),
            _c("pagamentos", "inteiro", "Quantidade de pagamentos."),
            _c("fonte", "texto", "tce_sp ou tce_rs."),
        ),
    ),
    # ---- Dinheiro público, emendas, agenda e votos (ondas de out/2026) ----
    Conjunto(
        nome="emendas_federais",
        titulo="Emendas ao orçamento federal",
        descricao="Emendas parlamentares ao orçamento da União: uma linha por emenda, "
        "localidade e ação (o código da emenda se repete). Valores empenhado e pago.",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/emendas",
        fontes=("transparencia_emendas",),
        filtros="Só autor parlamentar (nome público) e totais; sem CPF.",
        sql="""SELECT id, codigo, ano, tipo, individual, autor_codigo, autor_nome, parlamentar_id,
                      localidade, municipio_ibge, uf, funcao, acao, valor_empenhado, valor_pago
               FROM emenda ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("codigo", "texto", "Código da emenda (repete por localidade e ação)."),
            _c("ano", "inteiro", "Ano da emenda."),
            _c("tipo", "texto", "Tipo de emenda como a fonte informa."),
            _c("individual", "booleano", "Se é emenda individual."),
            _c("autor_codigo", "texto", "Código do autor no orçamento."),
            _c("autor_nome", "texto", "Nome do autor (parlamentar ou colegiado).", True),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id, quando ligado."),
            _c("localidade", "texto", "Localidade de aplicação, como a fonte informa."),
            _c("municipio_ibge", "texto", "Código IBGE do município, quando é um município."),
            _c("uf", "texto", "Estado, como a fonte informa."),
            _c("funcao", "texto", "Função orçamentária (área)."),
            _c("acao", "texto", "Ação orçamentária."),
            _c("valor_empenhado", "decimal", "Valor empenhado, em reais."),
            _c("valor_pago", "decimal", "Valor pago, em reais."),
        ),
    ),
    Conjunto(
        nome="emendas_pagamentos",
        titulo="Emendas pagas por favorecido (prefeituras e entidades)",
        descricao="Valor pago de emendas a prefeituras, fundos municipais e entidades sem fins "
        "lucrativos, por emenda, favorecido e mês.",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/emendas",
        fontes=("transparencia_emendas",),
        filtros="Favorecido que não é CNPJ de 14 dígitos sai sem nome e sem código. "
        "pessoa_id só quando o vínculo da pessoa é forte ou foi revisado.",
        sql=f"""WITH {VP}
                SELECT p.id, p.emenda_codigo, p.ano_emenda, p.ano_mes, p.autor_codigo,
                       p.autor_nome, p.parlamentar_id,
                       CASE WHEN p.pessoa_id IN (SELECT pessoa_id FROM vp)
                            THEN p.pessoa_id END AS pessoa_id,
                       p.tipo,
                       CASE WHEN {_doc_pf("p.favorecido_codigo")} THEN NULL
                            ELSE p.favorecido END AS favorecido,
                       CASE WHEN length({_doc("p.favorecido_codigo")}) = 14
                            THEN {_doc("p.favorecido_codigo")} END AS favorecido_cnpj,
                       p.natureza, p.grupo, p.municipio_ibge, p.valor
                FROM emenda_pagamento p ORDER BY p.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("emenda_codigo", "texto", "Código da emenda."),
            _c("ano_emenda", "inteiro", "Ano da emenda."),
            _c("ano_mes", "inteiro", "Mês do pagamento (AAAAMM)."),
            _c("autor_codigo", "texto", "Código do autor."),
            _c("autor_nome", "texto", "Nome do autor.", True),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id, quando ligado."),
            _c("pessoa_id", "inteiro", "pessoas_publicas.id, quando publicável."),
            _c("tipo", "texto", "individual, especial, bancada, comissao ou relator."),
            _c("favorecido", "texto", "Quem recebeu (vazio se não for CNPJ).", True),
            _c("favorecido_cnpj", "texto", "CNPJ do favorecido."),
            _c("natureza", "texto", "Natureza jurídica do favorecido."),
            _c("grupo", "texto", "prefeitura ou entidade."),
            _c("municipio_ibge", "texto", "Código IBGE do município do favorecido."),
            _c("valor", "decimal", "Valor pago, em reais."),
        ),
    ),
    Conjunto(
        nome="emendas_pagamentos_sem_codigo",
        titulo="Pagamentos de emendas sem código da emenda",
        descricao="Pagamentos do arquivo por favorecido cujo código de emenda a fonte marca "
        "como 'Sem informação'. Autor e ano da emenda não vêm da fonte.",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/emendas",
        fontes=("transparencia_emendas",),
        filtros="Favorecido que não é CNPJ de 14 dígitos sai sem nome e sem código.",
        sql=f"""SELECT id, ano_mes, tipo, autor_codigo, autor_nome,
                       CASE WHEN {_doc_pf("favorecido_codigo")} THEN NULL
                            ELSE favorecido END AS favorecido,
                       CASE WHEN length({_doc("favorecido_codigo")}) = 14
                            THEN {_doc("favorecido_codigo")} END AS favorecido_cnpj,
                       natureza, grupo, municipio_ibge, valor
                FROM emenda_pagamento_sem_codigo ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("ano_mes", "inteiro", "Mês do pagamento (AAAAMM)."),
            _c("tipo", "texto", "Tipo de emenda, quando a fonte traz."),
            _c("autor_codigo", "texto", "Código do autor, como veio."),
            _c("autor_nome", "texto", "Autor como veio ('Sem informação' ou relator-geral).", True),
            _c("favorecido", "texto", "Quem recebeu (vazio se não for CNPJ).", True),
            _c("favorecido_cnpj", "texto", "CNPJ do favorecido."),
            _c("natureza", "texto", "Natureza jurídica do favorecido."),
            _c("grupo", "texto", "prefeitura ou entidade."),
            _c("municipio_ibge", "texto", "Código IBGE do município do favorecido."),
            _c("valor", "decimal", "Valor pago, em reais."),
        ),
    ),
    Conjunto(
        nome="emendas_transferencias",
        titulo="Destino do dinheiro das emendas (convênios e transferências especiais)",
        descricao="Convênio ou plano de ação de transferência especial ligado a uma emenda, "
        "com situação, valores e vigência.",
        orgao="Portal da Transparência (CGU) e TransfereGov",
        url="https://portaldatransparencia.gov.br/emendas e https://transferegov.sistema.gov.br/",
        fontes=("transferegov_convenios", "transferegov_especiais"),
        filtros="Beneficiário que não é CNPJ de 14 dígitos sai sem nome e sem número.",
        sql=f"""SELECT id, tipo, emenda_codigo, ano_emenda, identificador, situacao,
                       relatorio_gestao,
                       CASE WHEN {_doc_pf("beneficiario_cnpj")} THEN NULL
                            ELSE beneficiario END AS beneficiario,
                       CASE WHEN length({_doc("beneficiario_cnpj")}) = 14
                            THEN {_doc("beneficiario_cnpj")} END AS beneficiario_cnpj,
                       uf, municipio_ibge, orgao_concedente, objeto, valor_total,
                       valor_repassado, valor_contrapartida, inicio_vigencia, fim_vigencia
                FROM emenda_transferencia ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("tipo", "texto", "convenio ou especial."),
            _c("emenda_codigo", "texto", "Código da emenda."),
            _c("ano_emenda", "inteiro", "Ano da emenda."),
            _c("identificador", "texto", "Número do convênio ou código do plano de ação."),
            _c("situacao", "texto", "Situação como a fonte informa."),
            _c("relatorio_gestao", "texto", "Andamento do relatório de gestão."),
            _c("beneficiario", "texto", "Quem recebeu (vazio se não for CNPJ).", True),
            _c("beneficiario_cnpj", "texto", "CNPJ do beneficiário."),
            _c("uf", "texto", "Estado."),
            _c("municipio_ibge", "texto", "Município do beneficiário, quando identificado."),
            _c("orgao_concedente", "texto", "Órgão que repassa."),
            _c("objeto", "texto", "Objeto, como a fonte descreve.", True),
            _c("valor_total", "decimal", "Valor total, em reais."),
            _c("valor_repassado", "decimal", "Valor repassado, em reais."),
            _c("valor_contrapartida", "decimal", "Contrapartida, em reais."),
            _c("inicio_vigencia", "data", "Início da vigência."),
            _c("fim_vigencia", "data", "Fim da vigência."),
        ),
    ),
    Conjunto(
        nome="emendas_convenios",
        titulo="Ligação entre emendas e convênios",
        descricao="Qual convênio nasceu de qual emenda; os dados do convênio estão em "
        "emendas_transferencias (coluna identificador).",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/emendas",
        fontes=("transferegov_convenios",),
        filtros="Nenhum.",
        sql="""SELECT emenda_codigo, numero_convenio FROM emenda_convenio
               ORDER BY emenda_codigo, numero_convenio""",
        colunas=(
            _c("emenda_codigo", "texto", "Código da emenda."),
            _c("numero_convenio", "texto", "Número do convênio."),
        ),
    ),
    Conjunto(
        nome="emendas_relator_indicacoes",
        titulo="Indicações de emendas de relator-geral (LOA 2022)",
        descricao="Beneficiários indicados por parlamentares nas emendas de relator-geral, "
        "pela planilha oficial da Comissão Mista de Orçamento. O valor é o solicitado.",
        orgao="Congresso Nacional (Comissão Mista de Orçamento)",
        url="https://www.congressonacional.leg.br/",
        fontes=("congresso_emendas_relator",),
        filtros="Beneficiário que não é CNPJ de 14 dígitos sai sem nome e sem número.",
        sql=f"""SELECT numero, ano, data_cadastro, parlamentar_id, autor_nome,
                       CASE WHEN {_doc_pf("beneficiario_cnpj")} THEN NULL
                            ELSE beneficiario END AS beneficiario,
                       CASE WHEN length({_doc("beneficiario_cnpj")}) = 14
                            THEN {_doc("beneficiario_cnpj")} END AS beneficiario_cnpj,
                       uf, orgao, unidade, acao, objeto, valor_solicitado
                FROM emenda_relator_indicacao ORDER BY numero""",
        colunas=(
            _c("numero", "inteiro", "Número da indicação."),
            _c("ano", "inteiro", "Ano."),
            _c("data_cadastro", "data", "Data do cadastro."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id."),
            _c("autor_nome", "texto", "Parlamentar que pediu.", True),
            _c("beneficiario", "texto", "Beneficiário (vazio se não for CNPJ).", True),
            _c("beneficiario_cnpj", "texto", "CNPJ do beneficiário."),
            _c("uf", "texto", "Estado."),
            _c("orgao", "texto", "Órgão."),
            _c("unidade", "texto", "Unidade orçamentária."),
            _c("acao", "texto", "Ação orçamentária."),
            _c("objeto", "texto", "Objeto.", True),
            _c("valor_solicitado", "decimal", "Valor solicitado, em reais."),
        ),
    ),
    Conjunto(
        nome="emendas_estaduais",
        titulo="Emendas parlamentares estaduais",
        descricao="Emendas de deputados estaduais ao orçamento do estado, como cada portal "
        "estadual publica (uma linha por proposta, indicação, instrumento ou empenho). "
        "valor_previsto se repete nas linhas da mesma emenda (codigo): some uma vez por "
        "codigo; pago e empenhado somam-se entre linhas.",
        orgao="Governos e assembleias estaduais (portais de transparência de cada estado)",
        url="https://github.com/ (ver docs/FONTES_DE_DADOS.md do projeto; a coluna fonte "
        "diz o portal)",
        fontes=(
            "seplan_ac_emendas",
            "transparencia_al_emendas",
            "sefaz_ba_emendas",
            "sefaz_es_emendas",
            "segov_mg_emendas",
            "seplag_pe_emendas",
            "sctransferencias_emendas",
            "dadosabertos_go_emendas",
            "dadospb_emendas",
            "transparencia_df_emendas",
            "transparencia_ma_emendas",
            "transparencia_se_emendas",
        ),  # fmt: skip
        filtros="Favorecido que não é CNPJ de 14 dígitos sai sem nome e sem número. "
        "pessoa_id do autor só quando o vínculo é forte ou foi revisado.",
        sql=f"""WITH {VP}
                SELECT e.id, e.uf, e.ano, e.codigo, e.proposta, e.transferencia, e.tipo,
                       e.autor_nome,
                       CASE WHEN e.pessoa_id IN (SELECT pessoa_id FROM vp)
                            THEN e.pessoa_id END AS pessoa_id,
                       e.municipio_ibge, e.municipio_nome,
                       CASE WHEN {_doc_pf("e.favorecido_cnpj")} THEN NULL
                            ELSE e.favorecido_nome END AS favorecido_nome,
                       CASE WHEN length({_doc("e.favorecido_cnpj")}) = 14
                            THEN {_doc("e.favorecido_cnpj")} END AS favorecido_cnpj,
                       e.favorecido_natureza, e.orgao, e.instrumento, e.objeto,
                       e.situacao_proposta, e.situacao_transferencia, e.valor_previsto,
                       e.valor_empenhado, e.valor_pago, e.fonte
                FROM emenda_estadual e ORDER BY e.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("uf", "texto", "Estado."),
            _c("ano", "inteiro", "Ano da emenda."),
            _c("codigo", "texto", "Código da emenda."),
            _c("proposta", "texto", "Chave da linha na fonte (única na UF)."),
            _c("transferencia", "texto", "Código da transferência, quando há."),
            _c("tipo", "texto", "individual ou bancada."),
            _c("autor_nome", "texto", "Autor, como a fonte informa.", True),
            _c("pessoa_id", "inteiro", "pessoas_publicas.id, quando publicável."),
            _c("municipio_ibge", "texto", "Código IBGE do município."),
            _c("municipio_nome", "texto", "Município como veio da fonte."),
            _c("favorecido_nome", "texto", "Quem recebeu (vazio se não for CNPJ).", True),
            _c("favorecido_cnpj", "texto", "CNPJ do favorecido."),
            _c("favorecido_natureza", "texto", "Natureza do favorecido."),
            _c("orgao", "texto", "Órgão concedente."),
            _c("instrumento", "texto", "Instrumento (convênio, repasse...)."),
            _c("objeto", "texto", "Objeto.", True),
            _c("situacao_proposta", "texto", "Situação da proposta."),
            _c("situacao_transferencia", "texto", "Situação da transferência."),
            _c("valor_previsto", "decimal", "Valor previsto (repete por emenda)."),
            _c("valor_empenhado", "decimal", "Valor empenhado, em reais."),
            _c("valor_pago", "decimal", "Valor pago, em reais."),
            _c("fonte", "texto", "Identificador do portal estadual."),
        ),
    ),
    Conjunto(
        nome="empresas",
        titulo="Cadastro de empresas que aparecem nos dados",
        descricao="Empresas (CNPJ) que aparecem como fornecedor, beneficiário ou sancionada "
        "nos conjuntos, da base aberta do CNPJ da Receita Federal. Só os CNPJs de interesse.",
        orgao="Receita Federal do Brasil",
        url="https://dadosabertos.rfb.gov.br/CNPJ/",
        fontes=("receita_empresas",),
        filtros="MEI cuja razão social traz CPF sai sem nome (nome_omitido = verdadeiro). "
        "Sem sócios.",
        sql="""SELECT cnpj, razao_social, nome_omitido, nome_fantasia, natureza_juridica,
                      municipio_ibge, uf, situacao, referencia
               FROM empresa WHERE length(cnpj) = 14 ORDER BY cnpj""",
        colunas=(
            _c("cnpj", "texto", "CNPJ (14 dígitos)."),
            _c("razao_social", "texto", "Razão social (vazia se nome_omitido).", True),
            _c("nome_omitido", "booleano", "Verdadeiro quando o nome trazia CPF e foi omitido."),
            _c("nome_fantasia", "texto", "Nome fantasia.", True),
            _c("natureza_juridica", "texto", "Código da natureza jurídica."),
            _c("municipio_ibge", "texto", "Código IBGE do município."),
            _c("uf", "texto", "Estado."),
            _c("situacao", "texto", "Código da situação cadastral (02 ativa)."),
            _c("referencia", "texto", "Mês da base da Receita usada."),
        ),
    ),
    Conjunto(
        nome="sancoes_empresas",
        titulo="Sanções da CGU a empresas (CEIS e CNEP)",
        descricao="Sanções a empresas que aparecem como fornecedoras nos dados do acervo.",
        orgao="Controladoria-Geral da União",
        url="https://portaldatransparencia.gov.br/sancoes",
        fontes=("cgu_sancoes",),
        filtros="Só CNPJ de 14 dígitos; sanção a pessoa física não entra.",
        sql="""SELECT cadastro, codigo, cnpj, nome, categoria, abrangencia, orgao, inicio, fim,
                      processo
               FROM sancao_empresa WHERE length(cnpj) = 14 ORDER BY cadastro, codigo""",
        colunas=(
            _c("cadastro", "texto", "CEIS ou CNEP."),
            _c("codigo", "texto", "Código da sanção."),
            _c("cnpj", "texto", "CNPJ da empresa."),
            _c("nome", "texto", "Nome da empresa.", True),
            _c("categoria", "texto", "Categoria da sanção."),
            _c("abrangencia", "texto", "Onde a sanção vale."),
            _c("orgao", "texto", "Órgão sancionador."),
            _c("inicio", "data", "Início."),
            _c("fim", "data", "Fim."),
            _c("processo", "texto", "Número do processo.", True),
        ),
    ),
    Conjunto(
        nome="gastos_locais_fora",
        titulo="O que ficou fora da soma da verba indenizatória",
        descricao="Gastos de gabinete que a planilha da casa traz mas que não entram na soma "
        "por mês (hoje, comprovantes sem data na CLDF), para o que falta não parecer zero.",
        orgao="Câmara Legislativa do Distrito Federal",
        url="https://www.cl.df.gov.br/",
        fontes=("cldf",),
        filtros="Só contagem e valor total por mandato e ano.",
        sql="""SELECT mandato_id, ano, linhas, valor, linhas_valor_ilegivel, motivo
               FROM gasto_local_fora ORDER BY mandato_id, ano""",
        colunas=(
            _c("mandato_id", "inteiro", "mandatos_locais.id."),
            _c("ano", "inteiro", "Ano da planilha."),
            _c("linhas", "inteiro", "Linhas fora da soma."),
            _c("valor", "decimal", "Valor das linhas de valor legível, em reais."),
            _c("linhas_valor_ilegivel", "inteiro", "Linhas de valor ilegível."),
            _c("motivo", "texto", "Por que ficou fora."),
        ),
    ),
    Conjunto(
        nome="agenda_compromissos",
        titulo="Agenda pública de ministros e outros agentes (e-Agendas)",
        descricao="Reuniões, eventos, audiências, viagens e presentes registrados na agenda "
        "pública de pessoas da base que são agentes públicos federais.",
        orgao="Controladoria-Geral da União (e-Agendas)",
        url="https://eagendas.cgu.gov.br/",
        fontes=("eagendas",),
        filtros="Só pessoa com vínculo forte ou revisado. Participantes privados só pela "
        "entidade que representam, sem nome. Detalhes de viagem e presente (ofertante, item) "
        "ficam de fora.",
        sql=f"""WITH {VP}
                SELECT a.id, a.pessoa_id, a.tipo, a.id_registro, a.cargo, a.orgao,
                       a.data_inicio, a.data_fim, a.hora_inicio::text AS hora_inicio,
                       a.hora_fim::text AS hora_fim, a.forma, a.assunto, a.local, a.origem,
                       a.destino,
                       CASE WHEN a.tipo NOT IN ('viagem', 'presente') THEN a.detalhes END
                         AS detalhes,
                       a.participantes_publicos, a.n_participantes_publicos,
                       a.entidades_privadas, a.n_participantes_privados, a.publicado_em
                FROM agenda_compromisso a
                WHERE a.pessoa_id IN (SELECT pessoa_id FROM vp) ORDER BY a.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("tipo", "texto", "reuniao, evento, audiencia, audiencia_publica, viagem, presente."),
            _c("id_registro", "inteiro", "Número do registro no e-Agendas."),
            _c("cargo", "texto", "Cargo na data."),
            _c("orgao", "texto", "Órgão."),
            _c("data_inicio", "data", "Data de início."),
            _c("data_fim", "data", "Data de fim."),
            _c("hora_inicio", "texto", "Hora de início."),
            _c("hora_fim", "texto", "Hora de fim."),
            _c("forma", "texto", "Presencial ou Virtual."),
            _c("assunto", "texto", "Assunto, como o agente registrou.", True),
            _c("local", "texto", "Local.", True),
            _c("origem", "texto", "Origem (viagem)."),
            _c("destino", "texto", "Destino (viagem)."),
            _c("detalhes", "texto", "Detalhes (não vão em viagem nem presente).", True),
            _c("participantes_publicos", "json", "Agentes públicos: nome, cargo, órgão.", True),
            _c("n_participantes_publicos", "inteiro", "Quantos agentes públicos."),
            _c("entidades_privadas", "json", "Entidades dos participantes privados.", True),
            _c("n_participantes_privados", "inteiro", "Quantos participantes privados."),
            _c("publicado_em", "data", "Data de publicação na agenda."),
        ),
    ),
    Conjunto(
        nome="servidores_federais",
        titulo="Cargos de confiança de pessoas acompanhadas (SIAPE)",
        descricao="Cargos comissionados e funções de confiança de pessoas da base no cadastro "
        "de servidores do Portal da Transparência. primeiro_mes e ultimo_mes dizem em que "
        "meses o registro apareceu.",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/servidores",
        fontes=("cgu_servidores", "cgu_viagens_cne"),
        filtros="Só pessoa com vínculo forte ou revisado. Sem remuneração, CPF e matrícula.",
        sql=f"""WITH {VP}
                SELECT s.id, s.pessoa_id, s.origem, s.sigla, s.nivel, s.funcao, s.atividade,
                       s.orgao, s.orgao_superior, s.uf, s.situacao_vinculo, s.data_ingresso,
                       s.data_nomeacao, s.primeiro_mes, s.ultimo_mes
                FROM servidor_federal s
                WHERE s.pessoa_id IN (SELECT pessoa_id FROM vp) ORDER BY s.id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("origem", "texto", "siape (cadastro mensal) ou viagens (função do viajante)."),
            _c("sigla", "texto", "Sigla do cargo ou função (CCX, FEX, CD, DAS...)."),
            _c("nivel", "texto", "Nível."),
            _c("funcao", "texto", "Função."),
            _c("atividade", "texto", "Atividade."),
            _c("orgao", "texto", "Órgão."),
            _c("orgao_superior", "texto", "Órgão superior."),
            _c("uf", "texto", "Estado."),
            _c("situacao_vinculo", "texto", "Situação do vínculo."),
            _c("data_ingresso", "data", "Ingresso no serviço público."),
            _c("data_nomeacao", "data", "Nomeação no cargo."),
            _c("primeiro_mes", "data", "Primeiro mês em que o registro apareceu."),
            _c("ultimo_mes", "data", "Último mês em que o registro apareceu."),
        ),
    ),
    Conjunto(
        nome="viagens_federais_ano",
        titulo="Viagens a serviço de pessoas acompanhadas, por ano",
        descricao="Total por ano de viagens a serviço, diárias, passagens e outros gastos "
        "(Portal da Transparência).",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/viagens",
        fontes=("cgu_viagens",),
        filtros="Só pessoa com vínculo forte ou revisado. Sem destino, motivo e trecho.",
        sql=f"""WITH {VP}
                SELECT v.pessoa_id, v.ano, v.viagens, v.diarias, v.passagens, v.outros,
                       v.devolucao, v.ultima_viagem
                FROM viagem_federal_ano v
                WHERE v.pessoa_id IN (SELECT pessoa_id FROM vp) ORDER BY v.pessoa_id, v.ano""",
        colunas=(
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("ano", "inteiro", "Ano da viagem."),
            _c("viagens", "inteiro", "Quantidade de viagens."),
            _c("diarias", "decimal", "Diárias, em reais."),
            _c("passagens", "decimal", "Passagens, em reais."),
            _c("outros", "decimal", "Outros gastos, em reais."),
            _c("devolucao", "decimal", "Valores devolvidos, em reais."),
            _c("ultima_viagem", "data", "Início da última viagem do ano."),
        ),
    ),
    Conjunto(
        nome="cartao_corporativo_mes",
        titulo="Cartão de pagamento do governo federal, por portador e mês",
        descricao="Gastos no cartão (CPGF) em que o portador é pessoa da base, somados por "
        "órgão e mês.",
        orgao="Portal da Transparência (CGU)",
        url="https://portaldatransparencia.gov.br/cartoes",
        fontes=("cgu_cpgf",),
        filtros="Só pessoa com vínculo forte ou revisado. Sem favorecido e sem transação.",
        sql=f"""WITH {VP}
                SELECT c.pessoa_id, c.orgao, c.ano, c.mes, c.transacoes, c.total, c.saques
                FROM cpgf_portador_mes c
                WHERE c.pessoa_id IN (SELECT pessoa_id FROM vp)
                ORDER BY c.pessoa_id, c.ano, c.mes, c.orgao""",
        colunas=(
            _c("pessoa_id", "inteiro", "pessoas_publicas.id."),
            _c("orgao", "texto", "Órgão do cartão."),
            _c("ano", "inteiro", "Ano do extrato."),
            _c("mes", "inteiro", "Mês do extrato."),
            _c("transacoes", "inteiro", "Quantidade de transações."),
            _c("total", "decimal", "Total gasto, em reais."),
            _c("saques", "decimal", "Parte sacada em dinheiro, em reais."),
        ),
    ),
    Conjunto(
        nome="transferencias_uniao",
        titulo="Repasses da União a estados e municípios",
        descricao="Repasses por mês e bloco (FPE, FPM, IPI_EXP, FUNDEB_UNIAO, ROYALTIES, "
        "OUTRAS_OBRIG, LEGAIS_VOLUNTARIAS).",
        orgao="Tesouro Nacional e Portal da Transparência",
        url="https://www.tesourotransparente.gov.br/ e https://portaldatransparencia.gov.br/",
        fontes=("tesouro_transferencias", "portal_transferencias"),
        filtros="Nenhum; só totais por bloco.",
        sql="""SELECT ano, mes, uf, municipio_ibge, bloco, fonte, valor FROM transferencia_uniao
               ORDER BY ano, mes, uf, municipio_ibge, bloco, fonte""",
        colunas=(
            _c("ano", "inteiro", "Ano."),
            _c("mes", "inteiro", "Mês."),
            _c("uf", "texto", "Estado."),
            _c("municipio_ibge", "texto", "Código IBGE (vazio nos repasses ao estado)."),
            _c("bloco", "texto", "Tipo de repasse."),
            _c("fonte", "texto", "tesouro ou portal."),
            _c("valor", "decimal", "Valor, em reais."),
        ),
    ),
    Conjunto(
        nome="arrecadacao_uf",
        titulo="Arrecadação federal por estado e mês",
        descricao="Arrecadação da Receita Federal por domicílio fiscal do contribuinte. total "
        "soma todos os tributos; previdencia é a receita previdenciária.",
        orgao="Receita Federal do Brasil",
        url="https://dados.gov.br/",
        fontes=("receita_arrecadacao_uf",),
        filtros="Nenhum.",
        sql="SELECT uf, ano, mes, total, previdencia FROM arrecadacao_uf ORDER BY ano, mes, uf",
        colunas=(
            _c("uf", "texto", "Estado."),
            _c("ano", "inteiro", "Ano."),
            _c("mes", "inteiro", "Mês."),
            _c("total", "decimal", "Arrecadação total, em reais."),
            _c("previdencia", "decimal", "Receita previdenciária, em reais."),
        ),
    ),
    Conjunto(
        nome="populacao_ibge",
        titulo="População residente (IBGE)",
        descricao="Código de 1 dígito = Brasil, 2 = estado, 7 = município. origem: estimativa "
        "(SIDRA 6579) ou censo (SIDRA 9514, 2022).",
        orgao="IBGE",
        url="https://sidra.ibge.gov.br/",
        fontes=("ibge_populacao",),
        filtros="Nenhum.",
        sql="SELECT codigo, ano, valor, origem FROM populacao_ibge ORDER BY codigo, ano",
        colunas=(
            _c("codigo", "texto", "Código IBGE (1, 2 ou 7 dígitos)."),
            _c("ano", "inteiro", "Ano."),
            _c("valor", "inteiro", "Habitantes."),
            _c("origem", "texto", "estimativa ou censo."),
        ),
    ),
    Conjunto(
        nome="contas_municipios",
        titulo="Contas anuais dos municípios (SICONFI)",
        descricao="Receita realizada, despesa paga e despesa paga por função (área), por "
        "município e ano, como o município entregou ao Tesouro.",
        orgao="Tesouro Nacional (SICONFI)",
        url="https://siconfi.tesouro.gov.br/",
        fontes=("siconfi_contas",),
        filtros="Nenhum.",
        sql="""SELECT municipio_ibge, ano, populacao, receita_total, despesa_paga,
                      receita_propria, transf_uniao, despesa_por_area
               FROM contas_municipio ORDER BY ano, municipio_ibge""",
        colunas=(
            _c("municipio_ibge", "texto", "Código IBGE."),
            _c("ano", "inteiro", "Ano."),
            _c("populacao", "inteiro", "População usada pela fonte."),
            _c("receita_total", "decimal", "Receita realizada, em reais."),
            _c("despesa_paga", "decimal", "Despesa paga, em reais."),
            _c("receita_propria", "decimal", "Impostos, taxas e contribuições de melhoria."),
            _c("transf_uniao", "decimal", "Transferências da União, em reais."),
            _c("despesa_por_area", "json", "Despesa paga por função de governo: {área: reais}."),
        ),
    ),
    Conjunto(
        nome="contas_estados",
        titulo="Contas anuais dos estados (SICONFI)",
        descricao="Receita realizada, despesa paga e despesa paga por função, por estado "
        "(e DF) e ano.",
        orgao="Tesouro Nacional (SICONFI)",
        url="https://siconfi.tesouro.gov.br/",
        fontes=("siconfi_contas_estados",),
        filtros="Nenhum.",
        sql="""SELECT uf, ano, populacao, receita_total, despesa_paga, despesa_por_area
               FROM contas_estado ORDER BY ano, uf""",
        colunas=(
            _c("uf", "texto", "Estado."),
            _c("ano", "inteiro", "Ano."),
            _c("populacao", "inteiro", "População usada pela fonte."),
            _c("receita_total", "decimal", "Receita realizada, em reais."),
            _c("despesa_paga", "decimal", "Despesa paga, em reais."),
            _c("despesa_por_area", "json", "Despesa paga por função de governo: {área: reais}."),
        ),
    ),
    Conjunto(
        nome="canais_oficiais",
        titulo="Sites oficiais dos municípios",
        descricao="Prefeitura, câmara e portais de transparência de cada município, do "
        "catálogo versionado do projeto.",
        orgao="Sites oficiais de cada município (catálogo do Panóptico)",
        url="https://github.com/ (data/canais_oficiais.csv do repositório)",
        fontes=("canais_oficiais",),
        filtros="Nenhum.",
        sql="""SELECT municipio_ibge, tipo, url, sistema, verificado_em FROM canal_oficial
               ORDER BY municipio_ibge, tipo, url""",
        colunas=(
            _c("municipio_ibge", "texto", "Código IBGE."),
            _c("tipo", "texto", "prefeitura, camara, transparencia..."),
            _c("url", "texto", "Endereço oficial."),
            _c("sistema", "texto", "Sistema usado (sapl, betha, ipm...), quando conhecido."),
            _c("verificado_em", "data", "Quando o endereço foi verificado."),
        ),
    ),
    Conjunto(
        nome="proposicoes",
        titulo="Projetos de lei, PECs e afins (Câmara e Senado)",
        descricao="Projetos apresentados na Câmara e no Senado, com situação e ementa.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_proposicoes", "senado_proposicoes"),
        filtros="Sem texto integral nem tramitação.",
        sql="""SELECT id, casa, id_externo, sigla_tipo, numero, ano, ementa, data_apresentacao,
                      situacao, virou_lei, url, autor_descricao, origem, relator,
                      relator_parlamentar_id
               FROM proposicao ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "camara ou senado."),
            _c("id_externo", "texto", "Código na Casa."),
            _c("sigla_tipo", "texto", "PL, PLP, PEC, PDL..."),
            _c("numero", "inteiro", "Número."),
            _c("ano", "inteiro", "Ano."),
            _c("ementa", "texto", "Ementa oficial.", True),
            _c("data_apresentacao", "data", "Data de apresentação."),
            _c("situacao", "texto", "Situação como a Casa informa."),
            _c("virou_lei", "booleano", "Se virou lei."),
            _c("url", "texto", "Página oficial."),
            _c("autor_descricao", "texto", "Autor quando não é parlamentar."),
            _c("origem", "texto", "legislatura ou votada."),
            _c("relator", "texto", "Relator, como a Casa publica."),
            _c("relator_parlamentar_id", "inteiro", "parlamentares_federais.id do relator."),
        ),
    ),
    Conjunto(
        nome="proposicoes_autorias",
        titulo="Quem assinou cada proposição",
        descricao="Autoria de proposições por parlamentar federal.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_proposicoes", "senado_proposicoes"),
        filtros="Nenhum.",
        sql="""SELECT proposicao_id, parlamentar_id, primeiro_autor FROM autoria
               ORDER BY proposicao_id, parlamentar_id""",
        colunas=(
            _c("proposicao_id", "inteiro", "proposicoes.id."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id."),
            _c("primeiro_autor", "booleano", "Se é o primeiro autor."),
        ),
    ),
    Conjunto(
        nome="votacoes",
        titulo="Votações nominais no Plenário (Câmara e Senado)",
        descricao="Votações com placar e resultado como a Casa publica.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_votacoes", "senado_votacoes"),
        filtros="Nenhum.",
        sql="""SELECT id, casa, id_externo, data, descricao, proposicao, proposicao_id_externo,
                      proposicao_ementa, secreta, resultado, placar_sim, placar_nao,
                      placar_abstencao
               FROM votacao ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "camara ou senado."),
            _c("id_externo", "texto", "Código na Casa."),
            _c("data", "data", "Data."),
            _c("descricao", "texto", "Descrição oficial.", True),
            _c("proposicao", "texto", "Rótulo da proposição votada (PL 759/2015)."),
            _c("proposicao_id_externo", "texto", "Código da proposição na Casa."),
            _c("proposicao_ementa", "texto", "Ementa da proposição.", True),
            _c("secreta", "booleano", "Se foi votação secreta (sem voto nominal)."),
            _c("resultado", "texto", "aprovada ou rejeitada."),
            _c("placar_sim", "inteiro", "Votos sim."),
            _c("placar_nao", "inteiro", "Votos não."),
            _c("placar_abstencao", "inteiro", "Abstenções."),
        ),
    ),
    Conjunto(
        nome="votos",
        titulo="Voto de cada parlamentar federal em cada votação",
        descricao="Na Câmara só existe para quem votou; no Senado, para todos, com o código "
        "de ausência quando é o caso. partido é o do dia da votação.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_votacoes", "senado_votacoes"),
        filtros="Nenhum.",
        sql="""SELECT votacao_id, parlamentar_id, voto, partido FROM voto
               ORDER BY votacao_id, parlamentar_id""",
        colunas=(
            _c("votacao_id", "inteiro", "votacoes.id."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id."),
            _c("voto", "texto", "Voto como a Casa registra."),
            _c("partido", "texto", "Partido no dia da votação."),
        ),
    ),
    Conjunto(
        nome="discursos",
        titulo="Discursos em Plenário (sumário oficial)",
        descricao="Discursos de dias com votação nominal: só o sumário oficial e os links, "
        "nunca a transcrição.",
        orgao="Câmara dos Deputados e Senado Federal",
        url="https://dadosabertos.camara.leg.br/ e https://legis.senado.leg.br/dadosabertos/",
        fontes=("camara_discursos", "senado_discursos"),
        filtros="Sem transcrição.",
        sql="""SELECT id, casa, id_externo, parlamentar_id, data, data_hora, fase, tipo, sumario,
                      url_texto, url_video, proposicao_id_externo, materias_citadas
               FROM discurso ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "camara ou senado."),
            _c("id_externo", "texto", "Código na Casa."),
            _c("parlamentar_id", "inteiro", "parlamentares_federais.id."),
            _c("data", "data", "Data."),
            _c(
                "data_hora",
                "datahora",
                "Data e hora, quando a fonte informa (horário de Brasília).",
            ),
            _c("fase", "texto", "Fase da sessão."),
            _c("tipo", "texto", "Tipo de discurso."),
            _c("sumario", "texto", "Sumário oficial.", True),
            _c("url_texto", "texto", "Link do texto oficial."),
            _c("url_video", "texto", "Link do vídeo oficial."),
            _c("proposicao_id_externo", "texto", "Projeto votado no dia, quando só 1 ou 2."),
            _c("materias_citadas", "inteiro", "Matérias citadas no dia."),
        ),
    ),
    Conjunto(
        nome="projetos_locais",
        titulo="Projetos de vereadores e deputados estaduais",
        descricao="Projetos que viram norma, do SAPL das casas, do ano atual e do anterior.",
        orgao="Câmaras municipais e assembleias legislativas",
        url="https://www.interlegis.leg.br/ (SAPL) e os portais de cada casa",
        fontes=("sapl_camaras", "sapl_assembleias"),
        filtros="Nenhum.",
        sql="""SELECT id, municipio_ibge, mandato_id, id_externo, tipo, numero, ano, ementa,
                      data_apresentacao, em_tramitacao, primeiro_autor, url
               FROM projeto_local ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("municipio_ibge", "texto", "Código IBGE (vazio nas assembleias)."),
            _c("mandato_id", "inteiro", "mandatos_locais.id."),
            _c("id_externo", "texto", "Código no SAPL."),
            _c("tipo", "texto", "Tipo de projeto."),
            _c("numero", "inteiro", "Número."),
            _c("ano", "inteiro", "Ano."),
            _c("ementa", "texto", "Ementa oficial.", True),
            _c("data_apresentacao", "data", "Data de apresentação."),
            _c("em_tramitacao", "booleano", "Se ainda tramita."),
            _c("primeiro_autor", "booleano", "Se é o primeiro autor."),
            _c("url", "texto", "Página oficial."),
        ),
    ),
    Conjunto(
        nome="votacoes_locais",
        titulo="Votações nominais em câmaras e assembleias",
        descricao="Votações nominais do SAPL (ano atual e anterior). Votações simbólicas "
        "não têm voto por parlamentar e não entram.",
        orgao="Câmaras municipais e assembleias legislativas",
        url="https://www.interlegis.leg.br/ (SAPL) e os portais de cada casa",
        fontes=("sapl_camaras", "sapl_assembleias"),
        filtros="Nenhum.",
        sql="""SELECT id, casa, uf, municipio_ibge, id_externo, materia, resultado, sim, nao,
                      abstencoes, data, url, materia_id_externo, materia_ementa,
                      projeto_local_id
               FROM votacao_local ORDER BY id""",
        colunas=(
            _c("id", "inteiro", "Identificador neste conjunto de dados."),
            _c("casa", "texto", "Tipo de casa."),
            _c("uf", "texto", "Estado."),
            _c("municipio_ibge", "texto", "Código IBGE (vazio nas assembleias)."),
            _c("id_externo", "texto", "Código da votação no SAPL."),
            _c("materia", "texto", "Matéria votada.", True),
            _c("resultado", "texto", "Resultado como a casa informa."),
            _c("sim", "inteiro", "Votos sim."),
            _c("nao", "inteiro", "Votos não."),
            _c("abstencoes", "inteiro", "Abstenções."),
            _c("data", "data", "Data."),
            _c("url", "texto", "Página oficial."),
            _c("materia_id_externo", "texto", "Código da matéria na casa."),
            _c("materia_ementa", "texto", "Ementa da matéria.", True),
            _c("projeto_local_id", "inteiro", "projetos_locais.id, quando ligado."),
        ),
    ),
    Conjunto(
        nome="votos_locais",
        titulo="Voto de cada vereador ou deputado estadual",
        descricao="Voto nominal de quem está no cargo, por votação.",
        orgao="Câmaras municipais e assembleias legislativas",
        url="https://www.interlegis.leg.br/ (SAPL) e os portais de cada casa",
        fontes=("sapl_camaras", "sapl_assembleias"),
        filtros="Nenhum.",
        sql="""SELECT votacao_id, mandato_id, voto FROM voto_local
               ORDER BY votacao_id, mandato_id""",
        colunas=(
            _c("votacao_id", "inteiro", "votacoes_locais.id."),
            _c("mandato_id", "inteiro", "mandatos_locais.id."),
            _c("voto", "texto", "Sim, Não, Abstenção, Não Votou..."),
        ),
    ),
)

POR_NOME = {c.nome: c for c in CONJUNTOS}
