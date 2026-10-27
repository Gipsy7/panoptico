# Plataformas compartilhadas de diário oficial municipal: levantamento nacional

Levantamento de 21 a 27/10/2026. Princípio: cobertura nacional, sem priorizar estado. O Querido Diário (OKBR) cobre hoje 441 municípios por raspadores (um por cidade), concentrados em poucos estados (SP 116, BA 72, RJ 33, SE 29, MA 28, PR 27, TO 26, RS 21, MG 20). Uma plataforma compartilhada publica o diário de dezenas ou centenas de municípios de uma vez, então o ganho está em ler a plataforma, não a cidade. Cada linha abaixo diz o que foi testado (curl e Python, com o User-Agent do projeto e sem nenhum truque) e o que ficou de fora e por quê.

Regra mantida em todos: o achado é sugestão em `diario_ato` (`revisado = false`) e só vai ao site depois da fila `python -m ingestion.revisar --tipo diario`. CPF nunca vai no trecho guardado. Detalhes de cada fonte: `docs/FONTES_DE_DADOS.md` (seção "Plataformas compartilhadas de diário municipal").

## 1. Plataformas abertas e implementadas

| Plataforma | URL | Municípios (últimos 90 dias) | UFs | Formato e busca | Robots e acesso | Conector |
|---|---|---:|---|---|---|---|
| **SIGPub** (Vox Tecnologia): diários de associações e federações de municípios, 24 instâncias | `diariomunicipal.com.br/<instância>/` | 2.089 | AL 98, AM 62, CE 108, GO 151, MG 490, PA 102, PB 118, PE 180, PR 244, RJ 15, RN 157, RO 51, RR 14, RS 294, SP 5 | PDF com texto, uma edição por dia e instância (mais as extraordinárias), de 1 a 14 MB e de 40 a 1.300 páginas; calendário por data (POST com o token CSRF da própria página); a busca avançada tem reCAPTCHA e não é usada | `robots.txt` com `Disallow:` vazio; host dos PDFs sem `robots.txt`; cerca de 1 conexão em 6 cai por tempo esgotado (repetimos com espera) | `ingestion/diarios/sigpub.py` (`sigpub_atos`) |
| **DOM/SC** (consórcio CIGA), pelos dados abertos | `dados.ciga.sc.gov.br` (conjuntos `domsc-publicacoes-de-MM-AAAA`) | 283 | SC 283 | ZIP de JSON por dia e faixa de horário, uma linha por publicação, com `municipio`, `entidade`, `categoria`, `texto` (HTML) e `url` do PDF do ato | o site `diariomunicipal.sc.gov.br` veda rastreadores (seção 2); o portal de dados abertos permite as páginas de conjunto e de download, veda `/api/` (não usada) e pede `Crawl-Delay: 10` (respeitado) | `ingestion/diarios/domsc.py` (`domsc_ciga_atos`) |

Instâncias do SIGPub e edições nos 90 dias: AMP (PR) 138, FAMURS (RS) 130, AMUPE (PE) 129, AROM (RO) 126, FEMURN (RN) 115, AEMERJ (RJ) 111, FAMUP (PB) 102, FAMEP (PA) 93, AGM (GO) 90, AMM-MG 88, APM (SP) 76, APRECE (CE) 72, AMR (RR) 71, AMA (AL) 68, AAM (AM) 67, FGM (GO) 67, Macatuba (SP) 67. Sem edição no período: AMM-MT (MT), APPM (PI), AMURC e Bahia (BA), Sergipe, Monte Alto (SP) e MS (última edição em 2020). A instância `ma` do seletor da página inicial não existe (redireciona para a inicial). As edições de AEMERJ e APM são curtas (13 e 7 matérias): publicam pouco por município.

Uma edição do SIGPub traz de 18 a 208 municípios (AMM-MG: 208 em 949 matérias; 68 matérias sem município por serem de consórcios e secretarias sem cidade no cabeçalho). O raspador `base/sigpub.py` do Querido Diário (MIT) usa a mesma lógica de calendário e cobre só 3 instâncias (AMA, Maceió e Macatuba); as outras 21 estavam sem leitura. O raspador do DOM/SC (issue #1426 do QD) ainda não existe, e o QD o faria pelo site que veda robôs.

## 2. Bloqueadas (pedido redigido, nada contornado)

| Plataforma | Municípios | Motivo | Pedido |
|---|---:|---|---|
| **DOM/SC, site** `diariomunicipal.sc.gov.br` | cerca de 290 (SC) | `robots.txt`: `User-agent: *` / `Disallow: /` (só Googlebot e Bingbot liberados). Resolvido sem o site, pelos dados abertos do próprio CIGA (seção 1). | não precisa |
| **FAMEM / SigaNet** `diariooficial.famem.org.br` | 217 (MA) | A lista de publicações abre, mas o texto só está no PDF de `painel.siganet.net.br`, cujo `robots.txt` veda `.pdf` (`Disallow: /*.pdf$`). Os raspadores por cidade do QD no MA (10 cidades) usam esse mesmo host. | [diario_famem_ma.md](pedidos/diario_famem_ma.md) |
| **AMUNES** `diariomunicipal.es.gov.br` | 78 (ES) | Certificado HTTPS autoassinado; não desligamos a verificação. | [diario_amunes_es.md](pedidos/diario_amunes_es.md) |
| **DOEM** `doem.org.br` | centenas (BA, PE, SE, PR; o QD tem 56 cidades) | Verificação de robô (BunkerWeb, exige JavaScript). | [diario_doem_dosp.md](pedidos/diario_doem_dosp.md) |
| **DOSP** `dosp.com.br` | dezenas (SP, MG, MS, PR, RS...; o QD tem 42) | A listagem só existe em `/api/...`, vedada pelo `robots.txt` (`Disallow: /api`). | [diario_doem_dosp.md](pedidos/diario_doem_dosp.md) |

## 3. Abertas, mas só por cidade (fase seguinte)

Plataformas de fornecedores em que cada cidade tem o próprio endereço. Não há índice de clientes: seria preciso uma lista município a endereço, hoje só obtida dos raspadores do QD, ou seja, de cidades que o QD já lê. O ganho líquido é baixo até haver um índice próprio; ficam registradas.

| Plataforma | Cidades no QD | UFs | Observação |
|---|---:|---|---|
| Instar (portal `/portal/diario-oficial` da prefeitura) | 111 | SP 78, MG 16, PR 6, MS 4, RS 4, RJ 2, MT 1 | cada portal com seu domínio e `robots.txt` |
| Município Online (`municipioonline.com.br`) | 26 | SE | host sem `robots.txt` |
| Atende.net (`<cidade>.atende.net/diariooficial`) | 22 | PR, RS | por subdomínio |
| DIOF / IO (`diof.io.org.br/api`, `sai.io.org.br`) | 21 | BA, AL, SE | API sem `robots.txt`; precisa do `cod_cliente` de cada cidade; sem índice |
| ADiários (`/diariooficial.php`) | 39 | CE, MA, PB, RN, RJ, PE, TO, PA, AP | por site da prefeitura |
| Barco Digital, Diário Oficial BR (TO), SigaNet por cidade (MA), Modernização (RJ), outros | 12, 10, 10, 6... | TO, MA, RJ | pequenos |

## 4. Não localizadas ou sem edição

AC, AP, DF, ES (só a AMUNES, bloqueada), MT (AMM-MT sem edição nos 90 dias), MS (instância SIGPub parada desde 2020), PI (APPM sem edição), BA (instâncias `amurc` e `bahia` do SIGPub sem edição; o resto em DOEM e DIOF/IO) e TO (nenhuma plataforma estadual de municípios achada) seguem só com o que o QD cobre. A busca por "diário oficial dos municípios" do Acre e do Tocantins não achou plataforma de associação; vale perguntar às associações (AMAC, ATM).

## 5. Municípios com diário lido, por UF (antes e depois)

"Antes" = municípios com raspador no Querido Diário (lista em `data/diarios_querido_diario_territorios.csv`, extraída dos raspadores em 21/10/2026). "Depois" = união com SIGPub e DOM/SC (evidência em `data/diarios_plataformas_municipios.csv`: municípios com ao menos uma matéria nos últimos 90 dias).

| UF | Municípios | Querido Diário (antes) | SIGPub | DOM/SC | Total depois | Novos |
|---|---:|---:|---:|---:|---:|---:|
| AC | 22 | 0 | 0 | 0 | 0 | 0 |
| AL | 102 | 4 | 98 | 0 | 100 | 96 |
| AM | 62 | 1 | 62 | 0 | 62 | 61 |
| AP | 16 | 3 | 0 | 0 | 3 | 0 |
| BA | 417 | 72 | 0 | 0 | 72 | 0 |
| CE | 184 | 13 | 108 | 0 | 117 | 104 |
| DF | 1 | 1 | 0 | 0 | 1 | 0 |
| ES | 78 | 3 | 0 | 0 | 3 | 0 |
| GO | 246 | 2 | 151 | 0 | 151 | 149 |
| MA | 217 | 28 | 0 | 0 | 28 | 0 |
| MG | 853 | 20 | 490 | 0 | 502 | 482 |
| MS | 79 | 10 | 0 | 0 | 10 | 0 |
| MT | 142 | 3 | 0 | 0 | 3 | 0 |
| PA | 144 | 3 | 102 | 0 | 104 | 101 |
| PB | 223 | 10 | 118 | 0 | 125 | 115 |
| PE | 185 | 5 | 180 | 0 | 182 | 177 |
| PI | 224 | 1 | 0 | 0 | 1 | 0 |
| PR | 399 | 27 | 244 | 0 | 256 | 229 |
| RJ | 92 | 33 | 15 | 0 | 45 | 12 |
| RN | 167 | 6 | 157 | 0 | 159 | 153 |
| RO | 52 | 1 | 51 | 0 | 51 | 50 |
| RR | 15 | 1 | 14 | 0 | 14 | 13 |
| RS | 497 | 21 | 294 | 0 | 304 | 283 |
| SC | 295 | 2 | 0 | 283 | 284 | 282 |
| SE | 75 | 29 | 0 | 0 | 29 | 0 |
| SP | 645 | 116 | 5 | 0 | 120 | 4 |
| TO | 139 | 26 | 0 | 0 | 26 | 0 |
| **BR** | 5571 | 441 | 2089 | 283 | 2752 | 2311 |

Antes: 441 municípios (7,9% dos 5.571). Depois: 2.752 (49,4%), ou 2.311 a mais. Seguem sem nenhum município: AC. Praticamente sem avanço: AP, BA, DF, ES, MA, MS, MT, PI, SE, TO (as plataformas deles estão nas seções 2, 3 ou 4).

Sugestões geradas na primeira carga (90 dias, todas `revisado = false`): SIGPub 559 sugestões para 311 pessoas em 199 municípios; DOM/SC 145 sugestões para 90 pessoas em 61 municípios. Em uma amostra de 12 sugestões do SIGPub, a pessoa é de fato a nomeada ou designada em cerca de dois terços; o resto é ruído esperado (nome em lista de comissão, em contrato, na assinatura), que a revisão humana descarta.

## 6. Contribuição para o Querido Diário

Não foi aberto PR externo. Vale sugerir ao QD (MIT): (1) instâncias SIGPub novas na base `BaseSigpubSpider` (uma classe de 4 linhas por instância com `CALENDAR_URL`: aam, aprece, agm, fgm, amm-mg, famep, famup, amupe, amp, aemerj, femurn, arom, amr, famurs, apm); (2) para o DOM/SC, usar os dados abertos do CIGA em vez do site (issue #1426): conjunto mensal `domsc-publicacoes-de-MM-AAAA` e o campo `municipio` para separar; (3) separar os municípios pelo cabeçalho (`ESTADO DE <UF>` / `PREFEITURA MUNICIPAL DE <CIDADE>`) dentro do PDF de uma associação, já que o QD guarda o PDF inteiro no território da associação.

## 7. Agenda e acesso

Os dois rodam no acervo local, como `querido_diario_atos` (que também não tem agenda): `python -m ingestion.acervo rodar --fonte sigpub_atos domsc_ciga_atos`, semanal. Não entraram em `deploy/vps/agenda/*.sh`: dependem do PyMuPDF (grupo `acervo`, fora da imagem de produção) e geram só fila de revisão, cujas decisões (`data/atos_revisados.csv`) a carga de pessoas já aplica na produção. Para agendar na VPS no futuro: incluir `pymupdf` nas dependências da imagem e acrescentar um passo `diarios` em `deploy/vps/agenda/camaras.sh` (domingo, trava `federal`). O SIGPub e o CIGA responderam normalmente a partir do Brasil; a VPS fica em São Paulo, então não exige runner especial. Acesso a partir de IP fora do Brasil não foi testado.
