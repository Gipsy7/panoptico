# Casos (curadoria com documentos oficiais)

Um **caso** junta o que órgãos oficiais produziram sobre um escândalo: processos, denúncias, acórdãos, relatórios de CPI, sanções. Cada pessoa entra **só pelo papel que um documento oficial lhe dá**. A imprensa não é fonte nem prova de ligação. Regras em `docs/DECISOES.md` ("acervo local e regras para Justiça e controle").

Carga: `python -m ingestion.curadoria`. Ela confere tudo e **reprova a carga inteira** se algo não bater. Caso com `rascunho = true` nunca é publicado.

## Uma pasta por caso: `data/casos/<slug>/`

### `caso.toml`

```toml
nome = "Mensalão (Ação Penal 470)"
periodo = "2005–2014"
resumo = "Texto factual, sem adjetivos: o que o STF julgou, quando e com que resultado geral."
conferido_em = 2026-10-09       # data em que os documentos foram conferidos
rascunho = true                 # tire só depois da revisão
```

### `documentos.csv`

| coluna | o que é |
|---|---|
| `codigo` | identificador curto, usado em `pessoas.csv` (ex.: `acordao`) |
| `tipo` | `processo`, `denuncia`, `acordao`, `sentenca`, `decisao`, `relatorio_cpi`, `sancao` ou `colaboracao` |
| `orgao` | quem produziu (ex.: `Supremo Tribunal Federal`) |
| `numero` | número como o órgão escreve (ex.: `AP 470`) |
| `numero_cnj` | número único do CNJ, se houver (conferido pelo dígito verificador) |
| `data` | `AAAA-MM-DD` |
| `url` | link **oficial** e `https` para o documento |
| `resumo` | uma frase factual sobre o documento |

### `pessoas.csv`

| coluna | o que é |
|---|---|
| `pessoa` | registro de origem da pessoa no Panóptico: `parlamentar:camara:204534`, `parlamentar:senado:5012`, `candidatura:2022:250001620281`. Use `/pessoas/{id}` para conferir |
| `nome_conferencia` | o nome da pessoa, para a carga conferir que o registro é o certo |
| `papel` | `investigado`, `indiciado`, `denunciado`, `reu`, `condenado`, `absolvido`, `arquivado`, `extinta_punibilidade`, `colaborador`, `citado_colaboracao` |
| `documento` | `codigo` do documento que dá esse papel |
| `data` | data do papel (se vazia, a do documento) |
| `descricao` | uma frase factual, como vai aparecer na linha do tempo |

Um papel por linha: quem foi denunciado e depois absolvido tem duas linhas, com os dois documentos. Absolvição, arquivamento e extinção têm o mesmo destaque da acusação.

## Processos consultados à mão: `data/curadoria/processos.csv`

Para fontes que bloqueiam acesso automático (STF, STJ). Uma pessoa consulta o portal público e anota o resultado. Colunas: `pessoa`, `nome_conferencia`, `tribunal`, `classe`, `numero`, `numero_cnj`, `papel`, `relator`, `data_autuacao`, `situacao`, `url`, `conferido_em`, `conferido_por`, `rascunho`. Processos sob segredo de justiça não entram.

## Casos na pasta

Todos são rascunho (`rascunho = true`): nada é publicado até a revisão humana. O que falta conferir está em `NOTAS.md` de cada pasta.

| caso | situação | documentos | pessoas ligadas |
|---|---|---|---|
| `mensalao` | rascunho; acórdão da AP 470 com data e link da notícia oficial do STF (conferido em 2026-10-18); réus fora da base | 1 | nenhuma (réus fora da base) |
| `sanguessugas` | rascunho; links do Congresso/Senado conferidos em 2026-10-10 | 4 (ficha RQN 77/2006-CN, Relatório Parcial nº 1, Relatório Final nº 6/2006-CN vol. I e II) | 9 parlamentares: 5 enviados ao Conselho de Ética (1 com absolvição informada pelo Relatório Final), 4 com arquivamento pela CPMI; desfechos no Conselho de Ética (Câmara e Senado) conferidos em 2026-10-18; STF: Laura Carneiro absolvida (AP 1014), Wellington Fagundes réu (Inq 2340, andamento a conferir); TCU a conferir |
| `zelotes` | rascunho; STF/TRF1/TCU dependem de conferência manual | 5 (RQS 407/2015, Relatório Final nº 17/2015 da CPI do CARF, sentença de 04/05/2016 da 10ª Vara Federal/DF, HC 138837 do STF, HC 588159 do STJ) | nenhuma ainda (réus e indiciados fora da base) |
| `cpi-pandemia` | rascunho; PDF do Relatório Final lido em 2026-10-18 e as 12 linhas conferidas; 3 petições no STF (Pet 10060, 10061, 10065) | 2 (Relatório Final aprovado, 26/10/2021; notícia do STF de 12/09/2022) | 12 com indiciamento proposto pela CPI (não é acusação formal), entre eles ex-ministros, parlamentares e o ex-presidente; encaminhamentos previstos no item 14 do relatório; desfecho no STF a conferir |
| `cpmi-8-de-janeiro` | rascunho; páginas oficiais da comissão e da 23ª Reunião conferidas em 2026-10-11; PDF do relatório bloqueado | 2 (página do Relatório Final aprovado, 23ª Reunião de 18/10/2023) | nenhuma ainda (lista de indiciados depende do PDF) |
| `cpi-brumadinho` | rascunho; relatório, ficha de tramitação e complementação de voto da Câmara conferidos em 2026-10-11 | 3 (REL 1/2019 CPIBRUMA, ficha com aprovação em 05/11/2019, Complementação de Voto nº 1) | nenhuma (os 22 indiciamentos propostos são de pessoas das empresas, fora da base) |

Quando um portal oficial bloqueia o acesso automático (verificação de segurança, 403), o link vai para a página oficial que responde e a lacuna é anotada em `NOTAS.md`; não contornamos o bloqueio.

Rascunho não é validado pela carga (ela o ignora por inteiro). Antes de tirar `rascunho = true`, rode a carga em cópia com `rascunho = false` para conferir pessoas e nomes.
