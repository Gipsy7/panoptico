# CGU: chave da API do Portal da Transparência (cadastro) e pedido de limite maior

**Não é pedido pela LAI.** A chave é gratuita e de autoatendimento; este arquivo é a instrução de cadastro e, só se o limite não bastar, o texto de um pedido de aumento.

**Órgão:** Controladoria-Geral da União (CGU), Portal da Transparência
**Canal:** cadastro da chave em https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email (a chave chega por e-mail e vai no cabeçalho `chave-api-dados`); dúvidas e pedido de limite maior pelo "Fale conosco" do Portal da Transparência (https://portaldatransparencia.gov.br) ou pela Ouvidoria da CGU no Fala.BR (https://falabr.cgu.gov.br)
**Base:** Decreto 8.777/2016 (Política de Dados Abertos); Lei 12.527/2011, art. 8º, §3º (acesso automatizado a dados abertos), apenas como fundamento do pedido de limite

## Instrução de cadastro

1. Abrir a página de cadastro acima e informar um e-mail de contato do projeto.
2. A chave chega por e-mail. **Nunca** colocar a chave no git, em log ou em relatório: guardar só como segredo (variável de ambiente do acervo local e segredo do GitHub Actions, no nome já usado pelo conector).
3. Usar a chave só nas rotas de dados abertos, identificar o robô no User-Agent ("Panoptico/0.1 (+https://panoptico.social.br)"), uma requisição por vez e respeitando o limite por minuto da API (na data da redação, 90 requisições por minuto de dia e 300 de madrugada, para a maioria das rotas; **confirmar na documentação**: https://api.portaldatransparencia.gov.br/swagger-ui.html).
4. Anotar em `docs/FONTES_DE_DADOS.md` a data do cadastro e o limite vigente (sem a chave).

## Pedido de limite maior (só se o limite padrão não bastar)

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública, com licença aberta (código AGPL-3.0 e dados em licença própria) e fonte oficial citada em cada dado. Usamos a API do Portal da Transparência com a chave cadastrada em [data], uma requisição por vez e com cache.

Para cobrir as emendas parlamentares, as sanções (CEIS, CNEP, CEAF) e as viagens e cartões dos agentes públicos que acompanhamos, a carga inicial exige mais requisições do que o limite padrão permite em uma janela razoável.

**Pedimos:** (1) a elevação do limite por minuto da nossa chave, durante a carga inicial ou de forma permanente, ou (2) a indicação do arquivo em lote equivalente (download de dados abertos), que preferimos por pesar menos nos servidores. **Periodicidade de uso:** carga inicial uma vez e atualizações diárias/semanais incrementais.

Atenciosamente,
[nome], Panóptico — [e-mail de contato]
