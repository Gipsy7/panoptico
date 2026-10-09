-- Fornecedores de prefeituras e câmaras (TCE) que têm como sócio uma pessoa que acompanhamos (eleitos e parlamentares).
--
-- Leitura correta: ser sócio de um fornecedor não é, por si só, irregular. Interessa
-- principalmente quando a pessoa tem ou teve mandato no mesmo município que pagou
-- (coluna "mesmo_municipio"), o que pode ser conflito de interesse e merece conferência.
-- Confira também a natureza do fornecedor: na primeira execução, os casos no mesmo
-- município foram um vice-prefeito no conselho de uma empresa de informática que atende a
-- prefeitura e um prefeito na diretoria da Santa Casa da cidade (entidade filantrópica que
-- recebe recursos do SUS pela prefeitura). Empresa pública, de economia mista ou entidade
-- filantrópica com dirigente político não é o mesmo que empresa privada de político.
-- Quadro de sócios da Receita, consultado pela API do Querido Diário; ligação pelos 6
-- dígitos visíveis do CPF + nome. Só os 1.000 maiores fornecedores e as empresas
-- sancionadas foram consultados.
select
    p.nome as socio,
    s.qualificacao,
    s.data_entrada,
    f.fornecedor,
    f.documento as cnpj,
    m.nome as municipio_pagador,
    m.uf,
    f.ano,
    f.orgao,
    f.valor_pago,
    (
        select string_agg(distinct c.cargo || ' ' || c.ano_eleicao || ' em ' || coalesce(c.unidade, ''), '; ')
        from pessoa_vinculo v
        join candidatura c
          on c.ano_eleicao = split_part(v.id_externo, ':', 1)::int
         and c.sq_candidato = split_part(v.id_externo, ':', 2)
        where v.pessoa_id = p.id and v.fonte = 'candidatura' and c.situacao_turno like 'ELEITO%'
    ) as mandatos,
    exists (
        select 1
        from pessoa_vinculo v
        join candidatura c
          on c.ano_eleicao = split_part(v.id_externo, ':', 1)::int
         and c.sq_candidato = split_part(v.id_externo, ':', 2)
        where v.pessoa_id = p.id and v.fonte = 'candidatura'
          and c.municipio_ibge = f.municipio_ibge
    ) as mesmo_municipio
from socio_pessoa s
join pessoa p on p.id = s.pessoa_id
join despesa_fornecedor f on f.documento = s.cnpj
join municipio m on m.ibge = f.municipio_ibge
order by mesmo_municipio desc, f.valor_pago desc
