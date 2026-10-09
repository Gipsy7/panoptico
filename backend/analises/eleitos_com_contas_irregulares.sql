-- Eleitos nas eleições mais recentes (2024 e 2026) que constam na lista do TCU de contas julgadas irregulares.
--
-- Leitura correta: ter contas julgadas irregulares não torna a pessoa inelegível por si
-- só. A Lei da Ficha Limpa (LC 64/1990, art. 1º, I, "g") exige irregularidade insanável
-- por ato doloso de improbidade, e quem decide é a Justiça Eleitoral, no registro da
-- candidatura. A lista do TCU traz só decisões transitadas em julgado e é atualizada todo
-- dia (nomes entram e saem). Ligação pelo CPF completo.
select
    p.nome,
    c.ano_eleicao,
    c.cargo,
    c.unidade,
    c.uf,
    c.partido,
    e.numero_processo,
    e.descricao,
    e.data as transito_em_julgado,
    e.situacao,
    e.fonte_url
from evento e
join pessoa p on p.id = e.pessoa_id
join pessoa_vinculo v on v.pessoa_id = p.id and v.fonte = 'candidatura'
join candidatura c
  on c.ano_eleicao = split_part(v.id_externo, ':', 1)::int
 and c.sq_candidato = split_part(v.id_externo, ':', 2)
where e.tipo = 'tcu_contas_irregulares'
  and c.ano_eleicao in (2024, 2026)
  and c.situacao_turno like 'ELEITO%'
order by c.ano_eleicao desc, c.uf, c.unidade, p.nome
