# Notas da curadoria: Mensalão (rascunho)

**Para a revisão humana (cerca de 30 a 45 min):** (1) abrir a íntegra do acórdão da AP 470 pelo link da notícia do STF (o link do arquivo é ftp) e confirmar número, data e placar; (2) conferir no portal do STF as datas do recebimento da denúncia (2007), do julgamento (2012) e dos embargos (até 2014), ainda não verificadas; (3) conferir na base, por CPF ou título, se algum dos 38 réus aparece como candidato depois de 2018. Sem esse último passo o caso continua sem pessoas ligadas.

Consulta em 2026-10-18 (uma requisição por vez, User-Agent do projeto): notícia do STF https://noticias.stf.jus.br/postsnoticias/ap-470-baixe-a-integra-do-acordao/ (HTTP 200).

## Resolvido
- **Acórdão da AP 470**: o documento deixou de ser "CONFERIR". Segundo a notícia institucional do STF, o acórdão foi publicado em 22/04/2013, com 8.405 páginas; 53 sessões plenárias; 38 réus, dos quais 25 condenados e 12 absolvidos; para um réu o STF decretou a nulidade desde a defesa prévia e baixou os autos à primeira instância. Data, link (https) e resumo foram atualizados em `documentos.csv`. A íntegra do acórdão está no link `ftp://ftp.stf.jus.br/ap470/InteiroTeor_AP470.pdf`, indicado pela própria notícia; não foi baixada (ftp, 8.405 páginas) e o número da página do dispositivo não foi conferido.

## Pendente
- O texto de `caso.toml` ainda diz "CONFERIR datas e números no acórdão": as datas de 2006 (denúncia), 2007 (recebimento), 2012 (mérito) e 2014 (embargos) não foram verificadas em documento oficial nesta rodada. O portal do STF bloqueia acesso automático (403).
- Nenhum réu da AP 470 está hoje na base do Panóptico (o recorte começa nas eleições de 2018). Uma busca anterior pelo nome encontrou só homônimos ("Pedro Correa Lima", vereador; "João Paulo Cunha Nunes", vereador). Esses **não** são os réus, e é por isso que a curadoria exige o registro de origem e o nome de conferência. Esta rodada não tinha acesso ao banco; não foi refeita a busca.
- Para o caso ligar pessoas, elas precisam estar na base: um réu que se candidatou depois de 2018 aparece pelo registro de candidatura (`candidatura:ano:sq`). A lista de condenados e absolvidos está no acórdão; a lista de papéis (condenado, absolvido) por réu ainda não foi montada.
