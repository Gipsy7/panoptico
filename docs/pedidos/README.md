# Pedidos de acesso a dados

Fontes que bloqueiam o acesso automático ou não publicam o dado em formato aberto. Pela regra do projeto (docs/DECISOES.md, "acervo local"), não contornamos bloqueios. Pedimos acesso e, se preciso, usamos a Lei de Acesso à Informação (LAI, Lei 12.527/2011).

| Órgão | O que pedimos | Situação | Pedido |
|---|---|---|---|
| STF | Liberação de acesso automatizado à consulta processual, ou arquivo com as partes de inquéritos e ações penais | a enviar | [stf_acesso.md](stf_acesso.md) |
| STF | Lista de inquéritos, ações penais e petições criminais com autoridade com foro como parte (LAI) | a enviar | [stf_lai.md](stf_lai.md) |
| STJ | Liberação de acesso automatizado, ou lista de ações penais originárias da Corte Especial (LAI) | a enviar | [stj_lai.md](stj_lai.md) |
| ALMG e ALESP | Votos nominais e presença em Plenário em formato aberto (LAI) | a enviar | — |
| Câmara dos Deputados | Justificativas de ausência em votações (LAI) | a enviar | — |

**Como enviar:**
- STF: Central do Cidadão (portal.stf.jus.br, "Central do Cidadão" → "Lei de Acesso à Informação"), ou e-mail da Ouvidoria.
- STJ: Ouvidoria, pelo formulário de acesso à informação.
- Prazo legal: 20 dias, prorrogáveis por mais 10. Cabe recurso se negado.

Ao enviar, anote aqui a data e o protocolo, e mude o `acesso` da fonte em `backend/ingestion/fontes.toml` para `pedido` ou `lai`.
