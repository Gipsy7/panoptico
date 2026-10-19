# ALMT (Mato Grosso): credencial de acesso público à API e dados de proposições, votos e presença

**Para:** Assembleia Legislativa de Mato Grosso (ALMT), Serviço de Informação ao Cidadão e Secretaria de Tecnologia da Informação
**Canal:** SIC / Ouvidoria da ALMT, pelo portal da Casa (https://www.al.mt.gov.br, "Transparência" / "Acesso à Informação"; confirmar o formulário na hora do envio)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado) e arts. 10 a 12; Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada deputado mostramos projetos, votos, presença e gastos, com dado oficial, link da fonte e data.

**O que encontramos:** a API da ALMT (`api.al.mt.gov.br`, com rotas de parlamentar, proposição e votação) exige **OAuth 2.0** e, segundo a própria página, é destinada a fornecedores da instituição. O `robots.txt` do site veda a pesquisa de proposições (`/proposicao?`), a ordem do dia e os documentos de parlamentares. Respeitamos as duas coisas e, por isso, hoje só mostramos a lista de deputados.

**O que pedimos**
1. Uma **credencial de acesso público** (client id e secret, ou chave de API) para a API de dados da ALMT, com direito de uso para fins de transparência, e a documentação dos campos e dos limites de uso; ou, se preferirem não conceder credencial, a publicação das mesmas informações em arquivo aberto.
2. Os dados: **proposições** de autoria (tipo, número, ano, ementa, data, autor, situação), **votações nominais** (matéria, data, deputado, voto, resultado) e **presença em Plenário** por sessão, de **01/02/2019 até hoje**.
3. **Formato:** a API em JSON, ou CSV (UTF-8) com dicionário de campos.
4. **Periodicidade:** atualização diária ou semanal. Identificamos o robô no User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"), com uma requisição por vez.

Atenciosamente,
[nome], Panóptico — [e-mail de contato]
