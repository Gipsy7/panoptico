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
)

POR_NOME = {c.nome: c for c in CONJUNTOS}
