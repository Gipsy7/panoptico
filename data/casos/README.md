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
