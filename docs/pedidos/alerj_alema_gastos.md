# ALERJ e ALEMA: gastos dos gabinetes (cota / verba indenizatória) em formato aberto ou autorização de leitura

Dois pedidos com o mesmo texto-base, um para cada Casa. Nos dois casos o dado está publicado em
página, mas o arquivo de regras do site (`robots.txt`) veda ou não deixa saber se a leitura
automatizada é permitida. A regra do projeto é não contornar nenhum bloqueio: **não coletamos**
essas páginas até receber orientação.

## 1. ALERJ (Rio de Janeiro)

**Para:** Assembleia Legislativa do Estado do Rio de Janeiro (ALERJ), Serviço de Informação ao Cidadão (e-SIC) e Diretoria responsável pelo DOCIGP
**Canal:** e-SIC da ALERJ (https://www.alerj.rj.gov.br, "Transparência" > "Acesso à informação"; confirmar o endereço na hora do envio)
**Base:** Lei 12.527/2011 (LAI), arts. 8º, §3º (dados abertos, legíveis por máquina) e 10 a 12; Lei 13.460/2017

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem
exerce função pública. Mostramos, na página de cada deputado, o que ele gasta, com a fonte e a
data da consulta.

A ALERJ publica os gastos de cada gabinete no sistema DOCIGP (`https://docigp.alerj.rj.gov.br`),
por deputado, mês e lançamento. O `robots.txt` desse endereço, porém, diz `User-agent: *` /
`Disallow: /`, isto é, veda a leitura automatizada de todo o sistema. Respeitamos essa regra.

**O que pedimos**
1. **O mesmo conteúdo em arquivo aberto**: CSV (UTF-8) ou JSON, com dicionário de campos, de
   **01/01/2025 até hoje**, uma linha por lançamento com: mês e ano de referência,
   deputado (nome parlamentar), tipo de despesa (centro de custo / natureza), data e valor
   (e, se houver, o valor devolvido ou glosado). Não precisamos do CPF nem do CNPJ do
   fornecedor; o nome do fornecedor só se for pessoa jurídica.
2. Atualização mensal, em endereço estável (por exemplo, no portal de dados abertos da Casa).
3. **Ou**, se a Casa preferir, autorização expressa para a leitura automatizada da API pública
   do DOCIGP (`/api/v1/`), com pausa entre as requisições, e a correção do `robots.txt` para
   refletir essa política.
4. A licença de uso, para citarmos a fonte.

## 2. ALEMA (Maranhão)

**Para:** Assembleia Legislativa do Estado do Maranhão (ALEMA), Serviço de Informação ao Cidadão (e-SIC) e Portal da Transparência
**Canal:** e-SIC da ALEMA (https://www.al.ma.leg.br, "Transparência"; confirmar o endereço na hora do envio)
**Base:** Lei 12.527/2011 (LAI), arts. 8º, §3º e 10 a 12; Lei 13.460/2017

Prezados,

O Portal da Transparência da ALEMA (`https://sistemas.al.ma.leg.br/transparencia/`) publica a
verba indenizatória por deputado e mês, em página (consulta "sintético", deputado a deputado).
O endereço `https://sistemas.al.ma.leg.br/robots.txt` responde **403 (Acesso negado)**: não
conseguimos saber se a Casa autoriza a leitura automatizada dessas páginas e, por isso, não as
coletamos.

**O que pedimos**
1. **Autorização expressa** (ou a indicação do canal próprio) para a leitura automatizada, com
   pausa entre as requisições, das páginas da verba indenizatória, e a correção do `robots.txt`
   (hoje 403) para que ele publique a política da Casa.
2. Preferencialmente, **o mesmo conteúdo em arquivo aberto**: CSV (UTF-8) ou JSON, de
   **01/01/2025 até hoje**, uma linha por despesa com mês e ano de competência, deputado (nome
   parlamentar), tipo de despesa e valor. Sem CPF ou CNPJ de fornecedor.
3. Atualização mensal, em endereço estável, e a licença de uso.

Não pedimos CPF, endereço nem qualquer dado pessoal além do nome parlamentar, que já é público.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
