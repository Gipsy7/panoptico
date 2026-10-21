# ALEPA (Pará): proposições e votações nominais em formato aberto

**Para:** Assembleia Legislativa do Estado do Pará (ALEPA), Serviço de Informação ao Cidadão e Diretoria de Tecnologia da Informação
**Canal:** SIC / Ouvidoria da ALEPA, pelo portal da Casa (https://www.alepa.pa.gov.br, "Transparência" / "Acesso à Informação"; confirmar o formulário na hora do envio)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado) e arts. 10 a 12; Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada deputado mostramos projetos, votos, presença e gastos, com dado oficial, link da fonte e data.

**O que encontramos:** a pesquisa de proposições e de votações nominais do portal da ALEPA é um componente que carrega os resultados por chamadas internas do navegador (`/Legislativo/CallbackPanelProposicoes`). A paginação (10 por página, cerca de 2.800 itens por ano) só funciona no navegador, e fora dele alcançamos só a primeira página. Não usamos automação de navegador para contornar isso. Hoje só mostramos a lista de deputados.

**O que pedimos**
1. **Proposições** de autoria de deputados (projetos de lei, lei complementar, emenda constitucional, decretos legislativos, resoluções, indicações e requerimentos): tipo, número, ano, ementa, data, autor e situação atual, de **01/02/2019 até hoje**.
2. **Votações nominais** em Plenário: matéria, data, deputado, voto e resultado, no mesmo período.
3. **Formato aberto:** CSV (UTF-8) ou JSON/XML, com dicionário de campos; ou uma API pública sem login e a documentação dela.
4. **Periodicidade:** atualização diária ou semanal, num endereço estável. Identificamos o robô no User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"), com uma requisição por vez.
5. A licença de uso dos dados.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
