# AMUNES (Espírito Santo): certificado HTTPS do Diário Oficial dos Municípios do ES

**Para:** Associação dos Municípios do Estado do Espírito Santo (AMUNES), responsável pelo Diário Oficial dos Municípios (https://www.diariomunicipal.es.gov.br)
**Canal:** contato da AMUNES (site oficial da associação); confirmar o canal na hora do envio
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (acesso automatizado, formatos abertos); Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Queremos ler o Diário Oficial dos Municípios do Espírito Santo, que atende os municípios capixabas, para mostrar (depois de conferência humana) atos de nomeação, exoneração e designação que citam prefeitos, vice-prefeitos e vereadores, sempre com link para a edição.

Em 21/10/2026, `https://diariomunicipal.es.gov.br` e `https://www.diariomunicipal.es.gov.br` apresentaram **certificado HTTPS autoassinado** (erro "CERTIFICATE_VERIFY_FAILED: self-signed certificate"). Não desligamos a verificação de segurança nem fixamos o certificado: ele não prova que o servidor é da AMUNES. Por isso o Espírito Santo ainda não é lido.

**Pedimos** que o endereço passe a usar certificado emitido por autoridade reconhecida (por exemplo, Let's Encrypt), e que informem se há exportação em lote (JSON/CSV com município, título, data e link) ou uma API de listagem de edições e de publicações. Leitura moderada: uma requisição por vez, identificada ("Panoptico/1.0 (+https://panoptico.social.br; contato@panoptico.social.br)"), respeitando o `robots.txt`.

**Periodicidade:** diária. Recorte: últimos 90 dias na primeira carga e, depois, só as edições novas.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
