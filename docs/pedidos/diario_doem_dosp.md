# DOEM e DOSP: diários oficiais de centenas de municípios atrás de verificação de robô e de API vedada

**Para:** DOEM (https://doem.org.br, diários de municípios da Bahia, Pernambuco, Sergipe e Paraná) e DOSP / Imprensa Oficial Municipal (https://dosp.com.br, diários de municípios de SP, MG, MS, PR, RS e outros)
**Canal:** contato de cada empresa/portal; confirmar o canal na hora do envio
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (acesso automatizado, formatos abertos); Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Queremos ler os diários oficiais municipais para mostrar, depois de conferência humana, atos de nomeação, exoneração e designação que citam prefeitos, vice-prefeitos e vereadores, sempre com link para o diário.

- **DOEM:** em 21/10/2026, a página inicial e as listagens (`doem.org.br/<UF>/<cidade>/diarios/AAAA/MM`) devolvem uma página de verificação de robô (BunkerWeb: "Bot Detection / JavaScript needs to be enabled"). Não contornamos esse tipo de verificação.
- **DOSP:** a listagem de edições só existe pela rota `dosp.com.br/api/index.php/dioe.js/...`, e o `robots.txt` do domínio veda `/api` e `/nuvem`. Respeitamos o `robots.txt`.

**Pedimos** uma destas formas: (1) liberar o acesso moderado e identificado ("Panoptico/1.0 (+https://panoptico.social.br; contato@panoptico.social.br)", uma requisição por vez) à listagem e aos PDFs das edições; (2) fornecer a lista de municípios atendidos e um índice de edições (município, número, data, link do PDF) em JSON/CSV; ou (3) indicar canal autorizado de acesso automatizado.

**Periodicidade:** diária. Recorte: últimos 90 dias na primeira carga e, depois, só as edições novas.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
