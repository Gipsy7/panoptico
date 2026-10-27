# ALRN: verbas de ressarcimento no novo portal da transparência (API com autenticação)

**Para:** Assembleia Legislativa do Rio Grande do Norte (ALRN), Serviço de Informação ao Cidadão e Transparência
**Canal:** formulário do SIC no portal da Casa (https://transparencia.al.rn.leg.br; confirmar o endereço na hora do envio)
**Base:** Lei 12.527/2011 (LAI), arts. 8º, §3º (dados abertos, legíveis por máquina) e 10 a 12; Lei 13.460/2017

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Mostramos, na página de cada deputado, o que ele gasta, com a fonte e a data da consulta.

Até outubro de 2026 líamos as verbas de ressarcimento em `https://www.al.rn.leg.br/portal/verbas`. Esse endereço agora responde 404 (o site principal exibe "Interrupção programada em andamento" e remete ao portal `https://transparencia.al.rn.leg.br`). A tela nova, `/verbas`, só entrega no HTML a lista de deputados e de meses; as notas vêm de `https://api-transparencia.al.rn.leg.br/verbas/...`, que responde **401 (não autorizado)** a quem não tem credencial. Como a regra do projeto é não contornar nenhum bloqueio, **não coletamos** as notas até recebermos orientação.

**O que pedimos**
1. A indicação do canal oficial (ou credencial pública) para ler, de forma automatizada e com pausa entre as requisições, as notas das verbas de ressarcimento; e o `robots.txt` do portal, que hoje responde 404.
2. Preferencialmente, o mesmo conteúdo em arquivo aberto (CSV UTF-8 ou JSON, com dicionário de campos), de 01/01/2025 até hoje: mês e ano, deputado (nome parlamentar), tipo de despesa, data da nota e valor. Não precisamos de CPF nem de CNPJ; o nome do fornecedor só se for pessoa jurídica.
3. Atualização mensal, em endereço estável, e a licença de uso.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
