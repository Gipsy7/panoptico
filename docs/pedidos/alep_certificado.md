# ALEP (Paraná): proposições da API pública (certificado) e verba de ressarcimento em CSV

**Para:** Assembleia Legislativa do Estado do Paraná (ALEP), Serviço de Informação ao Cidadão e Diretoria de Tecnologia da Informação
**Canal:** SIC / Ouvidoria da ALEP, pelo portal da Casa (https://www.assembleia.pr.leg.br, "Transparência" / "Acesso à Informação"; confirmar o formulário na hora do envio)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado) e arts. 10 a 12; Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada deputado estadual mostramos projetos, votos, presença e gastos, só com dado de fonte oficial, com link e data.

Já mostramos da ALEP os deputados, a presença em plenário e os votos nominais, lidos do site e do Portal da Transparência (`transparencia.assembleia.pr.leg.br`), respeitando o `robots.txt`, uma requisição por vez e identificando o robô no User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"). Faltam duas coisas, e por problemas técnicos que não contornamos.

**1. Proposições (projetos de autoria)**
A API de dados abertos anunciada na página "API de Dados Abertos" do Portal (`http://webservices.assembleia.pr.leg.br/api/public`) é a única fonte aberta de proposições. Em 19/10/2026 o endereço com HTTPS apresentava um **certificado autoassinado** (assunto "BLACKHOLE", SHA-256 `ae0f3aedfaa3bf2c17c9a37386a4faf21ca86354d27b885b68cd1a47c8ff903c`), respondia **403 Forbidden** a todas as rotas, inclusive `/robots.txt`, e depois deixou de aceitar conexões; o endereço `http://` também não respondeu. Não desligamos a verificação de segurança nem fixamos esse certificado: ele não prova que o servidor é da Assembleia. Pedimos que a API volte a responder com certificado emitido por autoridade reconhecida (por exemplo, Let's Encrypt ou o certificado do Estado), sem bloqueio de acesso automatizado moderado. A pesquisa legislativa do portal `consultas.assembleia.pr.leg.br` exige reCAPTCHA, e também não a contornamos.

**2. Gastos do gabinete e verba de ressarcimento**
A página "Verbas de Ressarcimento" do Portal da Transparência só devolve dados após um reCAPTCHA (rota `api/ressarcimento`, POST). Pedimos os dados em **CSV** (UTF-8, com dicionário de campos), num endereço estável, com: deputado, ano, mês, categoria da despesa e valor (a lista de favorecidos e o documento fiscal, se publicados, em colunas à parte). Se o Portal mantiver a consulta com reCAPTCHA, pedimos uma exportação anual sem ele, como a Assembleia Legislativa de Santa Catarina faz (`/gabinetes-parlamentares/csv/AAAA`).

**Periodicidade:** atualização mensal. Se houver documentação da API ou dos campos e limites de uso, pedimos o envio.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
