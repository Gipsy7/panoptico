-- Eleitos nas eleições mais recentes (2024 e 2026) com sanção da CGU (CEIS, CNEP, CEAF) ainda vigente.
--
-- Leitura correta: a maior parte das sanções a pessoas físicas no CEIS são condenações por
-- improbidade repassadas pelo CNJ, registradas como "Impedimento/proibição de contratar".
-- Isso não é o mesmo que suspensão dos direitos políticos, e não impede, por si só, o
-- exercício do mandato. A situação ("vigente até ...") foi calculada no dia da carga.
-- Ligação pelo CPF completo ou pelo CPF mascarado + nome.
select
    p.nome,
    c.ano_eleicao,
    c.cargo,
    c.unidade,
    c.uf,
    c.partido,
    e.data as inicio_da_sancao,
    e.situacao,
    e.numero_processo,
    e.descricao,
    e.fonte_url
from evento e
join pessoa p on p.id = e.pessoa_id
join pessoa_vinculo v on v.pessoa_id = p.id and v.fonte = 'candidatura'
join candidatura c
  on c.ano_eleicao = split_part(v.id_externo, ':', 1)::int
 and c.sq_candidato = split_part(v.id_externo, ':', 2)
where e.tipo = 'sancao'
  and e.situacao like 'vigente%'
  and c.ano_eleicao in (2024, 2026)
  and c.situacao_turno like 'ELEITO%'
order by c.ano_eleicao desc, c.uf, c.unidade, p.nome
