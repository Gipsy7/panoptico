# ALEP (Paraná): corrigir o certificado HTTPS da API pública, ou fornecer os dados em CSV

**Para:** Assembleia Legislativa do Estado do Paraná (ALEP), Serviço de Informação ao Cidadão e Diretoria de Tecnologia da Informação
**Canal:** SIC / Ouvidoria da ALEP, pelo portal da Casa (https://www.assembleia.pr.leg.br, "Transparência" / "Acesso à Informação"; confirmar o formulário na hora do envio)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado) e arts. 10 a 12; Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada deputado estadual mostramos projetos, votos, presença e gastos, só com dado de fonte oficial, com link e data.

A ALEP é a única Assembleia do país cujos dados não conseguimos mostrar por um problema técnico. A API pública (`https://webservices.assembleia.pr.leg.br/api/public/`) apresenta **certificado HTTPS autoassinado** (não emitido por autoridade certificadora reconhecida), e por isso navegadores e programas seguros recusam a conexão. Não desligamos a verificação de segurança para contornar o problema.

**O que pedimos (uma das duas opções)**
1. **Corrigir o certificado** do endereço acima, com um certificado emitido por autoridade reconhecida (por exemplo, Let's Encrypt, ou o certificado do Estado), mantendo a API aberta como está; ou
2. **Fornecer os dados em CSV** (UTF-8, com dicionário de campos), num endereço estável com HTTPS válido, com: deputados em exercício (nome parlamentar, partido); proposições de autoria (tipo, número, ano, ementa, data, autor, situação); votações nominais em Plenário (matéria, data, deputado, voto, resultado); presença em Plenário por sessão; e gastos de gabinete e cota parlamentar por mês e categoria.

**Periodicidade:** atualização diária ou semanal. Se houver documentação da API (campos e limites de uso), pedimos o envio. Identificamos o robô no User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"), com uma requisição por vez.

Atenciosamente,
[nome], Panóptico — [e-mail de contato]
