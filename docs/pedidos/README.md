# Pedidos de acesso a dados

Fontes que bloqueiam o acesso automático ou não publicam o dado em formato aberto. Pela regra do projeto (docs/DECISOES.md, "acervo local"), não contornamos bloqueios. Pedimos acesso e, se preciso, usamos a Lei de Acesso à Informação (LAI, Lei 12.527/2011).

| Órgão | O que pedimos | Situação | Pedido |
|---|---|---|---|
| STF | Liberação de acesso automatizado à consulta processual, ou arquivo com as partes de inquéritos e ações penais | a enviar | [stf_acesso.md](stf_acesso.md) |
| STF | Lista de inquéritos, ações penais e petições criminais com autoridade com foro como parte (LAI) | a enviar | [stf_lai.md](stf_lai.md) |
| STJ | Liberação de acesso automatizado, ou lista de ações penais originárias da Corte Especial (LAI) | a enviar | [stj_lai.md](stj_lai.md) |
| CNJ | Lote do Cadastro de Condenações por Improbidade e Inelegibilidade (CNIA), ou autorização para consultar por CPF em volume | a enviar | [cnj_cnia.md](cnj_cnia.md) |
| TSE | Tabela mensal de distribuição do Fundo Partidário em formato aberto (página bloqueada a robôs; o valor é obtido da prestação de contas dos partidos, que é o declarado por eles) | a enviar (redigido em 18/10/2026) | [tse_fundo_partidario.md](tse_fundo_partidario.md) |
| TCE-MG | Acesso à API de dados abertos (empenhos e pagamentos dos municípios) sem reCAPTCHA, ou arquivo anual em lote como o do TCE-RS (LAI); nenhum canal aberto alternativo existe | a enviar | [tce_mg.md](tce_mg.md) |
| CMO (Congresso) | Solicitantes das emendas de relator-geral (RP9) de 2020 e 2021 e das emendas de comissão (RP8), no formato da planilha da LOA 2022 (LAI) | a enviar | [cmo_rp9_solicitantes.md](cmo_rp9_solicitantes.md) |
| ALMG e ALESP | Votos nominais e presença em Plenário em formato aberto (LAI) | a enviar (redigido em 18/10/2026) | [almg_alesp_votos_presenca.md](almg_alesp_votos_presenca.md) |
| ALBA, ALES, ALESE, ALEGO, ALEPE, ALAP, ALEMA, ALECE, ALEMS e ALERJ | Votos nominais e/ou presença em Plenário em formato aberto (um pedido por Casa, só o que falta a cada uma) (LAI) | a enviar (redigido em 29/10/2026) | [assembleias_votos_presenca.md](assembleias_votos_presenca.md) |
| Câmara dos Deputados | Justificativas de ausência em votações (LAI) | a enviar (redigido em 18/10/2026) | [camara_justificativas_ausencia.md](camara_justificativas_ausencia.md) |
| ALEP (PR) | Corrigir o certificado HTTPS autoassinado da API pública, ou fornecer os dados em CSV (LAI) | a enviar (redigido em 18/10/2026) | [alep_certificado.md](alep_certificado.md) |
| ALMT (MT) | Credencial de acesso público à API (OAuth) para proposições, votos e presença (LAI) | a enviar (redigido em 18/10/2026) | [almt_proposicoes.md](almt_proposicoes.md) |
| ALEPA (PA) | Proposições e votações nominais em formato aberto (LAI) | a enviar (redigido em 18/10/2026) | [alepa_proposicoes.md](alepa_proposicoes.md) |
| TCE/SC | Base do Painel de Emendas (Farol), 2022–2026, com beneficiário e município (LAI, ADPF 854, IN TC 40/2025) | a enviar (redigido em 18/10/2026) | [tcesc_painel_emendas.md](tcesc_painel_emendas.md) |
| ALESC (SC) | Emendas impositivas estaduais por autor, município, favorecido, valor e situação, desde 2019 (LAI, ADPF 854) | a enviar (redigido em 18/10/2026) | [alesc_emendas_impositivas.md](alesc_emendas_impositivas.md) |
| 27 UFs (assembleias e governos) | Emendas parlamentares estaduais em formato aberto, modelo único (LAI, ADPF 854) | a enviar (redigido em 18/10/2026) | [emendas_estaduais_27_ufs.md](emendas_estaduais_27_ufs.md) |
| ALAP (AP) | Autorização de leitura automatizada (o `robots.txt` responde 403) ou arquivo aberto da CEAP por gabinete e mês (LAI) | a enviar (redigido em 20/10/2026) | [alap_gastos_ceap.md](alap_gastos_ceap.md) |
| FAMEM (MA) | PDFs das edições do Diário Oficial dos Municípios do Maranhão (217 municípios): o `robots.txt` do host dos PDFs (SigaNet) veda `.pdf`; pedimos liberação ou o texto das publicações | a enviar (redigido em 21/10/2026) | [diario_famem_ma.md](diario_famem_ma.md) |
| AMUNES (ES) | Certificado HTTPS válido (hoje autoassinado) no Diário Oficial dos Municípios do ES, ou exportação em lote | a enviar (redigido em 21/10/2026) | [diario_amunes_es.md](diario_amunes_es.md) |
| DOEM e DOSP | Acesso moderado e identificado aos diários de centenas de municípios (DOEM atrás de verificação de robô; DOSP com `/api` vedada no `robots.txt`), ou índice de edições em JSON/CSV | a enviar (redigido em 21/10/2026) | [diario_doem_dosp.md](diario_doem_dosp.md) |
| Câmaras com sistema Softcam (191, SC/RS/PR/SP/MG) | Liberar no `robots.txt` a leitura identificada das páginas públicas de vereadores, ou dados abertos (LAI) | a enviar (redigido em 27/10/2026) | [softcam_robots.md](softcam_robots.md) |
| 86 câmaras com robots.txt ou 403/429 ao robô | Liberar a leitura automatizada identificada, ou dados abertos (LAI) | a enviar (redigido em 27/10/2026) | [camaras_bloqueio_robos.md](camaras_bloqueio_robos.md) |
| 15 assembleias (AC, AM, AP, BA, DF, MA, MS, PA, PB, RN, RO, RR, RS, SE, TO) | Valor vigente do subsídio dos deputados, ato normativo, data de vigência e publicação permanente no portal de transparência (LAI) | a enviar (redigido em 29/10/2026) | [subsidio_deputados_estaduais.md](subsidio_deputados_estaduais.md) |
| CGU | Chave grátis da API do Portal da Transparência e, se preciso, limite maior (não é LAI: cadastro) | a fazer (redigido em 18/10/2026) | [cgu_chave_api.md](cgu_chave_api.md) |

**Como enviar:**
- STF: Central do Cidadão (portal.stf.jus.br, "Central do Cidadão" → "Lei de Acesso à Informação"), ou e-mail da Ouvidoria.
- STJ: Ouvidoria, pelo formulário de acesso à informação.
- TCE-MG: Ouvidoria do TCE-MG (tce.mg.gov.br, "Ouvidoria" / e-SIC).
- CNJ: Ouvidoria do CNJ (formulário em cnj.jus.br/ouvidoria) ou Serviço de Informação ao Cidadão; o cadastro é gerido pelo Comitê Gestor dos Cadastros Nacionais (Resolução CNJ 310/2020).
- Fala.BR (https://falabr.cgu.gov.br): pedidos a órgãos federais (TSE, Câmara, CGU); assembleias, governos e tribunais de contas estaduais têm e-SIC próprio (URL em cada pedido).
- Prazo legal: 20 dias, prorrogáveis por mais 10. Cabe recurso se negado.

Ao enviar, anote aqui a data e o protocolo, e mude o `acesso` da fonte em `backend/ingestion/fontes.toml` para `pedido` ou `lai`.
