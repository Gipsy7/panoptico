-- Fornecedores sancionados pela CGU que receberam pagamentos de prefeituras ou câmaras
-- (TCE) no ano em que a sanção estava vigente.
--
-- Leitura correta: pagar a uma empresa sancionada não é, por si só, irregular. A sanção
-- pode valer só no órgão que a aplicou ("No órgão sancionador") ou só na esfera dele, e o
-- pagamento pode ser de contrato anterior à sanção. A coluna "abrangencia" diz onde a
-- sanção vale; o cruzamento é um ponto de partida para conferir, não uma conclusão.
select
    m.nome as municipio,
    m.uf,
    f.ano,
    f.orgao,
    f.fornecedor,
    f.documento as cnpj,
    f.valor_pago,
    f.pagamentos,
    s.cadastro,
    s.categoria,
    s.abrangencia,
    s.orgao as orgao_sancionador,
    s.inicio as sancao_inicio,
    s.fim as sancao_fim,
    s.processo
from despesa_fornecedor f
join sancao_empresa s on s.cnpj = f.documento
join municipio m on m.ibge = f.municipio_ibge
where coalesce(s.inicio, date '1900-01-01') <= make_date(f.ano, 12, 31)
  and coalesce(s.fim, date '9999-12-31') >= make_date(f.ano, 1, 1)
order by f.valor_pago desc
