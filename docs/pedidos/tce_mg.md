# TCE-MG: empenhos e pagamentos dos municípios mineiros em formato aberto, sem reCAPTCHA

**Para:** Tribunal de Contas do Estado de Minas Gerais, Ouvidoria / Serviço de Informação ao Cidadão (e Diretoria responsável pelo SICOM e pelos Dados Abertos)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado) e Decreto Federal 8.777/2016 (Política de Dados Abertos)

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre pessoas que exercem função pública no Brasil. Publicamos apenas dados de fontes oficiais, sempre com link para a origem e a data da consulta.

Queremos mostrar, na página de cada município mineiro, para quem a prefeitura e a câmara municipal pagaram no ano (soma de pagamentos por credor, com o nome do credor e o valor), a partir do SICOM. O Tribunal do Rio Grande do Sul (TCE-RS) e o do Estado de São Paulo (TCE-SP) já publicam esse dado em arquivo ou API de acesso direto; no TCE-MG não conseguimos.

**O que encontramos (consulta de 09/10/2026):**
- `https://dadosabertos.tce.mg.gov.br/` é publicado como dados abertos, mas os arquivos saem da API `https://arabiasaudita.tce.mg.gov.br:8443/TCEMG-proxy-web/publico/apimoci/dados-abertos/dadosAbertos/...`, que responde **401** a qualquer chamada sem sessão, e o site leva o usuário a uma tela de reCAPTCHA (`TCEMG-proxy-web/login/captcha.jsf`).
- O "Fiscalizando com o TCE" usa o mesmo proxy, com 401 e reCAPTCHA.
- O certificado do servidor na porta 8443 não vem com a cadeia completa, e vários clientes padrão recusam a conexão.
- O portal de dados abertos do Estado (dados.mg.gov.br), o Base dos Dados, o Brasil.IO e o SICONFI não trazem empenhos ou pagamentos por credor dos municípios mineiros.

Como o reCAPTCHA existe justamente para impedir acesso automatizado, não o contornamos e não usamos automação de navegador. Por isso pedimos, em ordem de preferência:

1. a publicação, sem exigência de reCAPTCHA, de arquivos em lote (CSV ou similar) por município e ano, com empenhos, liquidações e pagamentos e o credor (nome e CPF/CNPJ), como os já disponíveis em dadosabertos.tce.mg.gov.br; ou
2. a liberação de acesso automatizado à API de dados abertos (credencial, chave de API ou lista de IPs), para uso com identificação do robô no cabeçalho User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"), uma requisição por vez, uma vez por mês; ou
3. o envio, por e-mail, dos arquivos dos exercícios de 2024 e 2025 de todos os municípios e câmaras, e a indicação de um endereço estável para as atualizações.

Também pedimos a indicação da licença de uso e do dicionário de dados (layout dos campos), para citarmos a fonte corretamente.

Ficamos à disposição para ajustar a frequência ou o horário das consultas.

Atenciosamente,
[nome], Panóptico — [e-mail de contato]
