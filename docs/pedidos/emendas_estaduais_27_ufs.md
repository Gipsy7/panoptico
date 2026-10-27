# Emendas parlamentares estaduais: modelo único para as 27 unidades da federação

Modelo para enviar **uma vez a cada Assembleia Legislativa** (e à Câmara Legislativa do DF) e **uma vez a cada Governo estadual** (secretaria de planejamento/fazenda, que executa o orçamento), 27 + 27 pedidos. Troque os campos entre colchetes. Em Santa Catarina, enviar também [alesc_emendas_impositivas.md](alesc_emendas_impositivas.md) e [tcesc_painel_emendas.md](tcesc_painel_emendas.md).

**Para:** [Assembleia Legislativa do Estado de UF / Governo do Estado de UF, Secretaria de ...], Serviço de Informação ao Cidadão (SIC) ou Ouvidoria
**Canal:** e-SIC estadual da UF (a maioria usa o Fala.BR, https://falabr.cgu.gov.br, ou sistema próprio; anotar o endereço usado de cada UF na tabela abaixo)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º e arts. 10 a 12; **ADPF 854 do STF** (transparência e rastreabilidade das emendas parlamentares, que alcança os demais entes da federação); Decreto Federal 8.777/2016

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Queremos mostrar, na página de cada deputado estadual e de cada município de [UF], quanto de emenda parlamentar foi indicado e para onde foi, com fonte oficial e data. Não encontramos esses dados em formato aberto no portal de transparência do [Estado de UF].

**O que pedimos**
1. A relação de **todas as emendas parlamentares estaduais** (individuais, de bancada, de comissão, impositivas, transferências especiais ou equivalentes), **desde 2019**, uma linha por emenda ou por pagamento, com: ano do orçamento, número da emenda, **autor** (deputado ou bancada), **município** de destino (código IBGE), **favorecido** (nome e CNPJ da entidade ou órgão; para pessoa física, só a categoria, sem CPF), objeto/finalidade, ação orçamentária, **valor indicado**, empenhado, liquidado e pago, **situação** (aprovada, em execução, executada, impedimento, cancelada) e data da última atualização.
2. **Formato aberto:** CSV (UTF-8) com dicionário de campos, ou API pública, sem exigência de cadastro ou reCAPTCHA.
3. **Periodicidade:** atualização mensal, num endereço estável. Se o dado já estiver publicado em algum painel, basta indicar o endereço e, se possível, a base completa.
4. A licença de uso dos dados.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br

## Controle dos envios (preencher ao enviar)

Preenchido em 27/10/2026 a partir de `docs/emendas_estaduais_levantamento.md` (nada enviado ainda). "O que pedir" é o trecho específico a acrescentar ao modelo acima; o canal é o e-SIC da UF, a confirmar no envio.

| UF | Casa/órgão | O que pedir | Canal (URL) | Data | Protocolo | Resposta |
|---|---|---|---|---|---|---|
| AC | — | Não precisa: dado aberto carregado (SEPLAN/AC). | | | | |
| AL | Governo de AL (SEFAZ/SEPLAG) e ALE | Os anos anteriores a 2026 (a consulta só tem 2026) e o CNPJ do beneficiário em campo próprio. | | | | |
| AM | Governo do AM (SEFAZ) e ALEAM | Arquivo aberto (CSV/API) das emendas; a consulta da SEFAZ não entrega dados sem navegador e o portal usa reCAPTCHA. | | | | |
| AP | Governo do AP e ALAP | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
| BA | Governo da BA (SEFAZ) e ALBA | Município de destino e beneficiário (CNPJ) de cada emenda no conjunto de dados abertos já publicado. | | | | |
| CE | Governo do CE (CGE/SEPLAG) e ALECE | Arquivo ou API das emendas (hoje só página HTML; a API de dados abertos não tem emendas). | | | | |
| DF | Governo do DF (SEEC) e CLDF | Município ou região administrativa e favorecido (CNPJ) de cada emenda; número da emenda (a API publica autor e valores por programa de trabalho, carregados desde 2016). | | | | |
| ES | — | Não precisa: dado aberto carregado (SEFAZ/ES). | | | | |
| GO | Governo de GO (SEFAZ/SERINT) e ALEGO | Arquivos de 2024 e 2025 refeitos sem notação científica no empenho, no processo e no CNPJ (hoje o empenho tem 5 valores em 2.594 linhas), com delimitador fixo e atualizados depois de julho/2025; município e posição atual de execução em 2021 e 2022; consulta EmendasGO sem captcha. Só 2023 está carregado. | | | | |
| MA | Governo do MA (SEPLAN/SEFAZ) e ALEMA | Anos anteriores a 2026 na exportação (o filtro só oferece 2026). | | | | |
| MG | — | Não precisa: dado aberto carregado (SEGOV/MG). | | | | |
| MS | Governo do MS e ALEMS | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
| MT | Governo do MT (SEPLAG) e ALMT | Arquivo aberto das emendas; a página de emendas não abre e o portal usa captcha. | | | | |
| PA | Governo do PA (SEPLAD) e ALEPA | Arquivo aberto do módulo de emendas do SIGPLAN; o portal da transparência não respondeu. | | | | |
| PB | Governo da PB e ALPB | Município de destino e favorecido (CNPJ) em campo próprio na API de dados abertos (`execucao_emendas`, carregada desde 2021). | | | | |
| PE | Governo de PE (SEPLAG) e ALEPE | Autor e município nos arquivos de 2012 a 2025 (hoje só empenhos); uma linha por empenho sem repetição por chamamento. | | | | |
| PI | Governo do PI (CGE/SEPLAN) e ALEPI | Uma série única de 2021 em diante com valor da emenda e execução contábil (empenhado, liquidado, pago) por emenda: a API pública traz 2021-2025 só por nota de empenho, sem valor da emenda, e 2026 com o valor mas a execução lançada à mão no detalhe de cada emenda. | | | | |
| PR | Governo do PR (SEFA) e ALEP | Arquivo aberto (hoje só painel Power BI). | | | | |
| RJ | Governo do RJ (SEPLAG) e ALERJ | Arquivo aberto (hoje só painel Qlik; o portal de dados abertos aponta para o painel). | | | | |
| RN | Governo do RN e ALRN | Arquivo aberto (hoje só painel Power BI). | | | | |
| RO | Governo de RO (SEPOG/COGES) e ALE-RO | Correção da consulta de emendas: empenhado, liquidado e pago vêm zerados em 2023-2025 (R$ 0 pago de R$ 489 milhões previstos em 2025, em empenhos com número emitido) e a base foi atualizada em 25/03/2026. | | | | |
| RR | Governo de RR e ALE-RR | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
| RS | Governo do RS (CAGE/SEFAZ) e ALRS | Arquivo aberto (os "dados abertos" do painel são o próprio Power BI). | | | | |
| SC | ALESC e TCE/SC | Ver alesc_emendas_impositivas.md e tcesc_painel_emendas.md (repasses fundo a fundo e às prefeituras). | | | | |
| SE | Governo de SE e ALESE | Número da emenda e valor empenhado na API já publicada. | | | | |
| SP | Governo de SP (SGRI/Fazenda) e ALESP | Correção do arquivo aberto: uma linha por emenda (ou por evento com chave), com valor previsto; hoje as linhas de execução se repetem e as somas não fecham (conferido de novo em 27/10/2026: o zip foi republicado em 23/10, mas o CSV dentro tem data de 29/05/2026: 238.420 linhas, uma emenda com 44.640). | | | | |
| TO | Governo do TO e ALETO | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
