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
| DF | — | Ainda não: há API aberta no Portal da Transparência do DF (carga a fazer). | | | | |
| ES | — | Não precisa: dado aberto carregado (SEFAZ/ES). | | | | |
| GO | Governo de GO (SEFAZ/SERINT) e ALEGO | Arquivo atualizado depois de julho/2025, sem CNPJ e empenho em notação científica, com delimitador fixo; consulta EmendasGO sem captcha. | | | | |
| MA | Governo do MA (SEPLAN/SEFAZ) e ALEMA | Anos anteriores a 2026 na exportação (o filtro só oferece 2026). | | | | |
| MG | — | Não precisa: dado aberto carregado (SEGOV/MG). | | | | |
| MS | Governo do MS e ALEMS | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
| MT | Governo do MT (SEPLAG) e ALMT | Arquivo aberto das emendas; a página de emendas não abre e o portal usa captcha. | | | | |
| PA | Governo do PA (SEPLAD) e ALEPA | Arquivo aberto do módulo de emendas do SIGPLAN; o portal da transparência não respondeu. | | | | |
| PB | Governo da PB e ALPB | Arquivo ou API documentada da consulta "Execução de emendas parlamentares impositivas". | | | | |
| PE | Governo de PE (SEPLAG) e ALEPE | Autor e município nos arquivos de 2012 a 2025 (hoje só empenhos); uma linha por empenho sem repetição por chamamento. | | | | |
| PI | Governo do PI e ALEPI | Arquivo ou API documentada das emendas (hoje só dentro das despesas da aplicação). | | | | |
| PR | Governo do PR (SEFA) e ALEP | Arquivo aberto (hoje só painel Power BI). | | | | |
| RJ | Governo do RJ (SEPLAG) e ALERJ | Arquivo aberto (hoje só painel Qlik; o portal de dados abertos aponta para o painel). | | | | |
| RN | Governo do RN e ALRN | Arquivo aberto (hoje só painel Power BI). | | | | |
| RO | — | Ainda não: há consulta com JSON no Portal da Transparência de RO (carga a fazer). | | | | |
| RR | Governo de RR e ALE-RR | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
| RS | Governo do RS (CAGE/SEFAZ) e ALRS | Arquivo aberto (os "dados abertos" do painel são o próprio Power BI). | | | | |
| SC | ALESC e TCE/SC | Ver alesc_emendas_impositivas.md e tcesc_painel_emendas.md (repasses fundo a fundo e às prefeituras). | | | | |
| SE | Governo de SE e ALESE | Número da emenda e valor empenhado na API já publicada. | | | | |
| SP | Governo de SP (SGRI/Fazenda) e ALESP | Correção do arquivo aberto: uma linha por emenda (ou por evento com chave), com valor previsto; hoje as linhas de execução se repetem e as somas não fecham. | | | | |
| TO | Governo do TO e ALETO | Indicar onde estão as emendas estaduais e publicar em arquivo aberto. | | | | |
