# FAMEM (Maranhão): edições do Diário Oficial dos Municípios em PDF, para leitura automatizada

**Para:** Federação dos Municípios do Estado do Maranhão (FAMEM), responsável pelo Diário Oficial dos Municípios do Maranhão (https://diariooficial.famem.org.br), e SigaNet (fornecedor do sistema, https://painel.siganet.net.br)
**Canal:** contato da FAMEM (site oficial da federação) e, se houver, e-SIC; confirmar o canal na hora do envio
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º (dados abertos, legíveis por máquina, acesso automatizado); Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada prefeito, vice-prefeito e vereador queremos mostrar, depois de conferência humana, os atos de nomeação, exoneração e designação que os citam nos diários oficiais, sempre com link para o diário e data.

O Diário Oficial dos Municípios do Maranhão atende os 217 municípios do estado e é o canal mais completo para esses atos. Conseguimos listar as publicações (título, órgão, tipo) em `https://diariooficial.famem.org.br/dom/dom/pesquisaPublicacoes/`, mas o **texto** só existe no PDF da edição, hospedado em `painel.siganet.net.br/upload/.../diario/*.pdf`. O `robots.txt` desse domínio veda a todos os robôs os arquivos `.pdf` (`Disallow: /*.pdf$`), e respeitamos: **não baixamos esses PDFs automaticamente**, nem trocamos o identificador do robô. Por isso o Maranhão ainda não é lido pelo Panóptico.

**Pedimos**, em uma destas formas:
1. liberar no `robots.txt` do `painel.siganet.net.br` os PDFs das edições do Diário Oficial dos Municípios (`/upload/*/cms/publicacoes/diario/`), para leitura moderada (uma requisição por vez, identificada: "Panoptico/1.0 (+https://panoptico.social.br; contato@panoptico.social.br)"); ou
2. fornecer o texto das publicações (JSON ou CSV, com órgão/município, título, tipo, data e link do ato), como faz o Consórcio CIGA para o DOM/SC em dados.ciga.sc.gov.br; ou
3. indicar outro endereço de acesso automatizado autorizado.

**Periodicidade:** diária (uma edição por dia útil). Recorte que usaremos: só os últimos 90 dias na primeira carga e, depois, as edições novas; só atos de pessoal que citam, pelo nome completo, pessoas que já acompanhamos; trecho de até 500 caracteres.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
