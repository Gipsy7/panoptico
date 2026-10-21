# TCE/SC: base do Painel de Emendas (Farol) em formato aberto

**Para:** Tribunal de Contas do Estado de Santa Catarina (TCE/SC), Ouvidoria / Serviço de Informação ao Cidadão e Diretoria de Informações Estratégicas (responsável pelo painel)
**Canal:** e-SIC / Ouvidoria do TCE/SC, pelo portal (https://www.tcesc.tc.br, "Ouvidoria" / "Acesso à Informação"; confirmar o formulário na hora do envio)
**Base:** Lei 12.527/2011 (LAI), art. 8º, §3º e arts. 10 a 12; ADPF 854 do STF (rastreabilidade e transparência das emendas parlamentares); **Instrução Normativa TC 40/2025 do TCE/SC** (transparência das emendas parlamentares)

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Na página de cada parlamentar e de cada cidade mostramos para onde foi o dinheiro das emendas, com dado oficial, link da fonte e data.

O Tribunal mantém o Painel de Emendas (Farol) com as emendas parlamentares executadas em Santa Catarina. Hoje o painel só permite consulta em tela. Para mostrar o dado ao cidadão e permitir conferência por terceiros, pedimos a base.

**O que pedimos**
1. A base completa do painel, de **2022 a 2026** (e atualizações), com emendas **federais, estaduais e municipais** executadas em SC, contendo, por emenda e por pagamento: ano, esfera (federal, estadual, municipal), tipo da emenda (individual, bancada, comissão, impositiva, "Pix"/transferência especial), código/número da emenda, **autor** (parlamentar ou bancada), **beneficiário** (nome e CNPJ de pessoa jurídica; para pessoa física, só a categoria, sem CPF), **município** de destino (código IBGE), órgão concedente, objeto/finalidade, valor empenhado, liquidado e pago, datas e situação.
2. **Formato aberto:** CSV (UTF-8) com dicionário de campos, ou API pública, sem reCAPTCHA.
3. **Periodicidade:** atualização mensal, num endereço estável (e a indicação de como as atualizações serão publicadas, conforme a IN TC 40/2025).
4. A licença de uso dos dados.

Não pedimos CPF nem dado pessoal de pessoa física beneficiária.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br

---

**Nota técnica (19/10/2026, não enviar):** o painel é um aplicativo Qlik Sense (`paineistransparencia.tce.sc.gov.br/extensions/appEmendasParlamentares/`) sem exportação em arquivo, e os hosts `servicos.tcesc.tc.br` e `paineistransparencia.tce.sc.gov.br` respondem 403 (Akamai) a um robô identificado, inclusive no `robots.txt`. Não contornamos. Enquanto isso, o site usa o SC Transferências (CGE/SC), que cobre só as emendas estaduais executadas por convênio ou termo de fomento (`docs/DECISOES.md`, 19/10/2026).
