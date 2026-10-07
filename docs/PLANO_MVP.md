# Panóptico: plano do MVP

**Domínio:** panoptico.social.br
**Slogan provisório:** Panóptico: quem te representa, às claras
**Ideia central:** inverter a lógica da vigilância. Em vez do Estado observar o cidadão, o cidadão passa a enxergar o poder público.

---

## 1. Objetivo do MVP

O usuário digita o CEP, vê quem o representa no nível federal (deputados federais e senadores) e abre um perfil de cada político com dados oficiais, sempre com link para a fonte.

**Por que só federal primeiro:** deputados federais e senadores são eleitos por estado, então o CEP só precisa resolver a UF. Os dados são centralizados e limpos. Bairro e município só passam a importar quando entrarem vereadores e emendas por cidade.

## 2. Fora do escopo do MVP (fase 2 em diante)

- Cadastro de usuário com endereço (LGPD: coleta mínima, consentimento, política de privacidade)
- Vereadores e deputados estaduais (cada Câmara/Assembleia publica de um jeito; começar por capitais)
- Destaque por bairro
- Processos e investigações (risco jurídico e dados fragmentados; exige curadoria e revisão)

## 3. Stack

| Camada | Tecnologia |
|---|---|
| Ingestão de dados | Python (httpx, pandas) com scripts agendados |
| Banco | PostgreSQL (Docker em desenvolvimento) |
| API | FastAPI |
| Front-end | Next.js + Tailwind |
| Hospedagem | a definir (começar barato) |

## 4. Fontes de dados

Confirmar endereços e formatos atuais na documentação de cada fonte antes de implementar.

| Dado | Fonte |
|---|---|
| Deputados, votações, proposições, presença, cota parlamentar (CEAP) | API de Dados Abertos da Câmara |
| Senadores, votações, matérias, despesas | API de Dados Abertos do Senado |
| Remuneração, emendas parlamentares | Portal da Transparência (CGU), exige chave gratuita |
| Candidaturas, bens declarados, prestação de contas | Dados abertos do TSE |
| CEP para UF e município | ViaCEP |
| Municípios e estados | API de localidades do IBGE |

## 5. Estrutura de pastas sugerida

```
panoptico/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── docs/
│   ├── PLANO_MVP.md
│   ├── FONTES_DE_DADOS.md      # endpoints, formato, frequência de atualização
│   └── DECISOES.md             # registro das decisões de arquitetura
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                # rotas (CEP, políticos, perfil)
│   │   ├── models/             # tabelas (SQLAlchemy)
│   │   ├── schemas/            # validação (Pydantic)
│   │   └── services/           # regras de negócio
│   ├── ingestion/
│   │   ├── camara/
│   │   ├── senado/
│   │   ├── transparencia/
│   │   └── run_all.py
│   ├── data/
│   │   ├── raw/                # dado bruto, nunca editado (fora do git)
│   │   └── processed/
│   └── tests/
├── frontend/                   # app Next.js
│   ├── app/
│   ├── components/
│   └── lib/
└── scripts/                    # utilitários (reset do banco, backup etc.)
```

## 6. Fases

### Fase 1: Fundação (dias 1 a 3)
- Criar repositório e estrutura de pastas
- Subir PostgreSQL com Docker
- Ambiente Python (venv) e FastAPI com rota de saúde
- Next.js rodando e conversando com a API

### Fase 2: Ingestão de parlamentares (semana 1)
- Baixar deputados e senadores em exercício (nome, partido, UF, foto, contato)
- Salvar bruto em `data/raw/` e tratado no banco
- Registrar fonte e data de atualização em cada registro

### Fase 3: Busca por CEP (semana 1 a 2)
- Endpoint: CEP → UF/município → lista de representantes
- Tela inicial com campo de CEP e cards dos políticos

**Marco:** primeira versão utilizável.

### Fase 4: Perfil do político (semana 2 a 3)
- Gastos da cota parlamentar (CEAP)
- Presença e votações
- Proposições
- Remuneração
- Cada informação com link para a fonte oficial

### Fase 5: Emendas por município (semana 3 a 4)
- Cruzar emendas parlamentares com o município do usuário
- Destacar quem enviou recursos para a cidade

### Fase 6: Polimento e publicação (semana 4 a 5)
- Layout responsivo e acessibilidade
- Página "Sobre as fontes" (de onde vem cada dado, quando foi atualizado)
- Política de privacidade
- Deploy e configuração do domínio panoptico.social.br

## 7. Princípios do projeto

1. **Dado bruto separado do tratado**, para reprocessar sem baixar tudo de novo.
2. **Toda informação com fonte e data de atualização.**
3. **Linguagem estritamente factual.** Sem notas, rankings subjetivos ou adjetivos nos perfis.
4. **Processos e investigações só com fonte oficial**, número do processo, data e status atual. Atenção a homônimos, arquivamentos e absolvições.
5. **Privacidade por padrão.** A função principal (buscar por CEP) funciona sem cadastro.

## 8. Design e experiência do usuário

O público-alvo é o grande público brasileiro, então a interface faz parte do produto, não é só acabamento.

**Mobile primeiro**
- Projetar a tela do celular antes da de computador (muitos acessos virão por links em grupos de WhatsApp).
- Site leve, pensando em conexão fraca.

**Uma ação principal na tela inicial**
- Campo grande de CEP, uma frase curta explicando o site e mais nada competindo por atenção.
- Link "não sei meu CEP" levando à busca por cidade e estado.

**Linguagem do dia a dia**
- Preferir "gastos do gabinete" a "CEAP", "projetos de lei" a "proposições" e "dinheiro enviado para sua cidade" a "emendas".
- O termo oficial aparece em letra menor, junto à fonte.

**Números com contexto**
- Mostrar o valor ao lado da média da Casa (Câmara ou Senado) como dado factual, sem juízo de valor.
- Sem notas, rankings subjetivos ou adjetivos (vale o princípio 3 da seção 7).

**Perfil em camadas**
- Topo: três ou quatro números-chave com visual simples (gastos, presença, projetos apresentados, remuneração).
- Abaixo, sob demanda: detalhes, tabelas e links das fontes oficiais.

**Identidade visual**
- Paleta sóbria e acolhedora, sem usar vermelho, azul ou verde-amarelo como cor principal (associação com partidos e lados políticos).
- O nome "Panóptico" é forte, então o visual deve compensar com tom amigável e aberto.

**Feito para compartilhar**
- Botão de compartilhar no WhatsApp em cada perfil.
- Imagem de pré-visualização (Open Graph) com nome, foto e dois ou três números.

**Acessibilidade**
- Contraste alto, fonte legível, navegação por teclado, textos alternativos nas imagens e gráficos.

**Ferramentas sugeridas**
- Tailwind + shadcn/ui (componentes acessíveis e rápidos de montar).
- Gráficos simples e leves; evitar bibliotecas pesadas no MVP.

**Critério de pronto para o front-end**
- Uma pessoa sem familiaridade com política consegue, em menos de um minuto, digitar o CEP, achar um representante e entender quanto ele gastou, sem ajuda.

---

## 9. Próximos passos no VS Code

1. Criar o repositório e a estrutura de pastas acima.
2. Subir o Postgres com `docker-compose.yml`.
3. Escrever o primeiro script de ingestão (deputados da Câmara).
4. Modelar o banco (parlamentar, mandato, despesa, proposição, fonte).
5. Criar a rota `GET /representantes?cep=...`.

## 10. Pendências

- [ ] Confirmar regras e renovação do domínio panoptico.social.br
- [ ] Conferir se o nome "Panóptico" está livre no INPI (serviços de informação)
- [ ] Reservar o nome nas redes sociais
- [ ] Gerar a chave da API do Portal da Transparência
