/**
 * Vocabulário do Argos: é este arquivo que se edita para ensiná-lo.
 *
 * Tudo aqui está sem acento, em minúsculas e sem pontuação (a frase é normalizada do mesmo
 * jeito antes de comparar). Frase com mais de uma palavra vale mais pontos que palavra solta.
 */
import type { Botao } from "./tipos";

/**
 * Palavras e frases que indicam cada assunto. A chave é o assunto; `secao:x` e `pagina:x` são
 * seções do perfil e páginas do site (ver `SECOES` e `PAGINAS`).
 */
export const PALAVRAS_ASSUNTO: Record<string, string[]> = {
  gastos: [
    "gasto", "gastos", "gastou", "gastar", "gastaram", "gastam", "gasta", "cota", "cotas", "despesa",
    "despesas", "reembolso", "reembolsos", "dinheiro", "custa", "custou", "gabinete", "ceap", "ceaps",
    "verba de gabinete", "quanto custa", "gastei", "gastando", "gastaria",
  ],
  presenca: [
    "presenca", "presencas", "faltou", "faltas", "falta", "faltam", "votou", "votacao", "votacoes",
    "compareceu", "ausente", "ausencia", "ausencias", "frequencia", "presente",
  ],
  projetos: [
    "projeto", "projetos", "lei", "leis", "propos", "propoe", "proposta", "propostas", "autor",
    "autoria", "apresentou", "projeto de lei", "pl", "pec", "propor",
  ],
  emendas: [
    "emenda", "emendas", "verba", "verbas", "mandou dinheiro", "enviou dinheiro",
    "destinou dinheiro", "destinou", "dinheiro para a cidade", "emendas pix", "emenda pix",
  ],
  representantes: [
    "cep", "moro", "minha cidade", "quem me representa", "meus deputados", "meu deputado",
    "meus senadores", "meus representantes", "quem sao meus", "minha regiao", "meu estado",
    "representante", "representantes", "quem representa", "moro em", "sou de", "meus parlamentares",
    "quem me representa", "quem e meu deputado", "quem sao os meus",
  ],
  comparar: [
    "comparar", "compare", "compara", "comparacao", "comparando", "comparativo", "versus", "vs",
    "lado a lado", "diferenca entre", "diferencas entre", "comparem",
  ],
  dinheiro_federal: [
    "dinheiro federal", "repasse", "repasses", "imposto", "impostos", "arrecadacao", "arrecadou",
    "tributo", "tributos", "dinheiro da uniao", "transferencias", "transferencia", "fpm",
    "verba federal", "recursos federais", "dinheiro enviado", "arrecada", "dinheiro do governo federal",
    "repasses federais", "impostos e repasses", "recebeu da uniao", "dinheiro que o governo mandou",
    "quanto entra", "quanto chega", "repassou", "repassa", "quanto mandou", "quanto repassou",
    "quanto enviou", "governo mandou", "uniao mandou", "governo repassou",
  ],
  partidos: [
    "partido", "partidos", "fundo partidario", "fundo eleitoral", "legenda", "dinheiro dos partidos",
    "contas dos partidos", "fundo", "siglas",
  ],
  lista: [
    "lista de deputados", "lista de senadores", "todos os deputados", "todos os senadores",
    "todos os parlamentares", "deputados", "senadores", "parlamentares", "quantos deputados",
    "quantos senadores", "quais deputados", "quais senadores", "bancada", "deputadas", "senadoras",
    "lista de parlamentares", "deputados federais",
  ],
  cidade: [
    "vereadores", "vereadoras", "camara municipal", "camara de vereadores", "prefeitura",
    "contas da prefeitura", "fornecedores", "licitacao", "licitacoes", "orcamento da cidade",
    "dados da cidade", "contratos da prefeitura", "contratos",
  ],
  eleicao: [
    "segundo turno", "2 turno", "eleicao", "eleicoes", "candidatos", "quem ganhou", "eleitos",
    "quem foi eleito", "urna", "data da eleicao", "quando e a eleicao", "turno", "eleito", "eleitas",
  ],
  salario: [
    "salario", "quanto ganha", "quanto recebe", "remuneracao", "subsidio", "holerite", "ganha por mes",
    "quanto ganham", "quanto recebem", "salarios", "recebe", "ganha", "ganham",
  ],
  executivo: [
    "presidente", "governador", "governadora", "prefeito", "prefeita", "quem governa",
    "chefe do executivo", "presidenta",
  ],
  "secao:votos": [
    "como votou", "como voto", "votos", "votou a favor", "votou contra", "como ele votou",
    "como ela votou", "historico de votos", "como vota", "votou em",
  ],
  "secao:candidatura": [
    "bens", "patrimonio", "candidatura", "campanha", "doadores", "declarou", "bens declarados",
    "quanto gastou na campanha", "tse", "doacoes recebidas",
  ],
  "secao:comissoes": ["comissoes", "comissao", "frentes parlamentares"],
  "secao:contato": [
    "telefone", "email", "e mail", "contato", "falar com", "como falo com", "whatsapp do gabinete",
    "endereco do gabinete", "mandar mensagem", "entrar em contato", "enderecos", "telefone do gabinete",
    "email do gabinete", "contato do gabinete",
  ],
  "secao:sancoes": [
    "processo", "processos", "sancao", "sancoes", "condenado", "condenacao", "investigado",
    "cassado", "cassacao", "ficha", "justica", "improbidade",
  ],
  "pagina:apoie": [
    "apoiar", "doar", "doacao", "doacoes", "contribuir", "pix", "como apoiar", "quero apoiar", "apoie",
    "quero ajudar", "ajudar o projeto", "fazer uma doacao",
  ],
  "pagina:apoiadores": ["apoiadores", "quem apoia", "quem ajuda"],
  "pagina:acessibilidade": [
    "acessibilidade", "libras", "leitor de tela", "deficiente", "daltonismo", "daltonico", "cego",
    "baixa visao", "alto contraste", "aumentar a letra", "letra maior",
  ],
  "pagina:status": ["status", "fora do ar", "caiu", "nao carrega", "nao abre", "esta funcionando", "travou"],
  "pagina:cobertura": ["cobertura", "quais cidades", "quais estados", "cidades que tem", "o que falta"],
  "pagina:projetos": [
    "o que esta sendo votado", "votacoes recentes", "pauta", "plenario", "o que foi votado",
    "o que vai ser votado", "votacoes de hoje", "ultimas votacoes", "ultimos projetos",
  ],
  "pagina:fontes": ["sobre as fontes", "metodologia", "como calcula", "como e calculado", "calculo"],
  "pagina:privacidade": ["privacidade", "politica de privacidade", "lgpd"],
  "pagina:codigo": ["codigo aberto", "github", "codigo fonte", "repositorio", "licenca do codigo"],
};

/** Ordem de desempate entre assuntos com a mesma pontuação (vence quem vem primeiro). */
export const ORDEM_ASSUNTO = [
  "comparar", "secao:votos", "pagina:projetos", "dinheiro_federal", "salario", "gastos", "presenca",
  "projetos", "emendas", "representantes", "cidade", "partidos", "eleicao", "executivo", "lista",
  "secao:candidatura", "secao:comissoes", "secao:contato", "secao:sancoes", "pagina:apoie",
  "pagina:apoiadores", "pagina:acessibilidade", "pagina:status", "pagina:cobertura", "pagina:fontes",
  "pagina:privacidade", "pagina:codigo",
];

/** O que cada seção do perfil mostra (a âncora é o `id` da seção em /parlamentar/[id]). */
export const SECOES: Record<string, { ancora: string; rotulo: string; texto: (nome: string) => string }> = {
  votos: {
    ancora: "votos",
    rotulo: "Ver os votos no perfil",
    texto: (n) => `Como ${n} votou em cada votação do Plenário está no perfil, com o resultado e a fonte.`,
  },
  candidatura: {
    ancora: "candidatura",
    rotulo: "Ver candidatura e bens no perfil",
    texto: (n) => `A candidatura de ${n}, os bens declarados e a campanha (dados do TSE) estão no perfil, com a fonte.`,
  },
  comissoes: {
    ancora: "comissoes",
    rotulo: "Ver comissões no perfil",
    texto: (n) => `As comissões de que ${n} participa e como votou nelas estão no perfil, com a fonte.`,
  },
  contato: {
    ancora: "contato",
    rotulo: "Ver contato do gabinete no perfil",
    texto: (n) => `O contato oficial do gabinete de ${n} (e-mail, telefone e página) está no perfil.`,
  },
  sancoes: {
    ancora: "sancoes",
    rotulo: "Ver registros oficiais no perfil",
    texto: (n) => `Os registros oficiais ligados a ${n} (sanções, processos e decisões de órgãos de controle) ficam no perfil, cada um com a fonte e a data. O Argos não os resume nem os avalia.`,
  },
};

/** Páginas do site que o Argos indica. */
export const PAGINAS: Record<string, { href: string; rotulo: string; texto: string }> = {
  apoie: {
    href: "/apoie",
    rotulo: "Apoie o Panóptico",
    texto: "O Panóptico é gratuito e sem anúncios; os custos são pagos por doações. A página Apoie mostra quanto custa e como ajudar. Doações não mudam nada no que o site mostra.",
  },
  apoiadores: {
    href: "/apoiadores",
    rotulo: "Apoiadores",
    texto: "A lista de apoiadores tem só quem autorizou o nome.",
  },
  acessibilidade: {
    href: "/acessibilidade",
    rotulo: "Acessibilidade",
    texto: "A página de acessibilidade explica o que o site faz para funcionar com leitor de tela, teclado, tela grande e contraste, e como avisar de um problema.",
  },
  status: {
    href: "/status",
    rotulo: "Estado do site e das fontes",
    texto: "A página de status mostra se o site e a API estão no ar e a data da última atualização de cada fonte.",
  },
  cobertura: {
    href: "/sobre-as-fontes/cobertura",
    rotulo: "Cobertura por estado",
    texto: "A página de cobertura mostra, estado por estado, o que já está no Panóptico e o que falta, e por quê.",
  },
  projetos: {
    href: "/projetos",
    rotulo: "Projetos e votações",
    texto: "Em Projetos e votações dá para buscar projetos de lei e ver as votações do Congresso, das assembleias e das câmaras, com resultado, quem votou e a fonte.",
  },
  fontes: {
    href: "/sobre-as-fontes",
    rotulo: "Sobre as fontes",
    texto: "A página Sobre as fontes lista as fontes oficiais e explica como cada número é calculado.",
  },
  privacidade: {
    href: "/privacidade",
    rotulo: "Privacidade",
    texto: "O CEP é usado só para achar a cidade e o estado e não é gravado. Não há cadastro nem cookies de rastreamento. Os detalhes estão na página de privacidade.",
  },
  codigo: {
    href: "https://github.com/Gipsy7/panoptico",
    rotulo: "Código aberto no GitHub",
    texto: "O código do Panóptico é aberto (licença AGPL-3.0) e os dados abertos têm licença própria.",
  },
};

/** Dúvidas sobre o site. `id` é o de `PERGUNTAS_FREQUENTES` ("sobre" = apresentação geral). */
export type FraseSite = { id: string; frases: string[] };

export const PALAVRAS_SITE: FraseSite[] = [
  { id: "fonte", frases: ["de onde vem", "de onde vem os dados", "fonte", "fontes", "origem dos dados", "dados oficiais"] },
  {
    id: "frequencia",
    frases: ["atualizado", "atualizados", "atualizada", "atualiza", "atualizacao", "com que frequencia", "quando atualiza", "desatualizado", "dados antigos"],
  },
  {
    id: "cobertura",
    frases: ["nao aparece", "cidade nao aparece", "nao aparecem", "nao encontrei", "nao tem vereador", "minha camara"],
  },
  {
    id: "cep",
    frases: [
      "guarda meu cep", "guarda o cep", "guardam meu cep", "guarda minha localizacao", "grava meu cep",
      "salva meu cep", "cookies", "rastreia", "meus dados",
    ],
  },
  {
    id: "nota",
    frases: ["da nota", "dao nota", "dar nota", "nota ou ranking", "ranking", "ligado a partido", "e de algum partido", "imparcial", "neutro"],
  },
  { id: "media-casa", frases: ["media da casa", "media da camara", "media do senado", "media"] },
  { id: "erro", frases: ["numero errado", "numero diferente", "errado", "corrigir", "erro", "reportar", "bug"] },
  {
    id: "quem-paga",
    frases: ["quem paga", "quem faz", "quem mantem", "quem financia", "quem criou", "patrocinio"],
  },
  {
    id: "dados",
    frases: ["usar os dados", "baixar", "download", "licenca", "dados abertos", "api", "copiar os dados", "planilha"],
  },
  {
    id: "sobre",
    frases: [
      "o que e o panoptico", "o que e panoptico", "o que e esse site", "o que e isso", "como funciona",
      "o que voces fazem", "para que serve", "o que e",
    ],
  },
];

/** Quem pede opinião ou nota. Vem antes de tudo: o Argos nunca opina. */
export const PALAVRAS_OPINIAO = [
  "em quem votar", "em quem voto", "em quem eu voto", "em quem devo votar", "em quem vou votar",
  "quem devo votar", "vale a pena votar", "corrupto", "corrupta", "corrupcao", "ladrao", "ladra",
  "presta", "nao presta", "e bom", "e boa", "e ruim", "bom deputado", "bom senador", "mau deputado",
  "melhor", "pior", "honesto", "honesta", "confiar", "recomenda", "recomendar", "merece", "bandido",
  "safado", "trabalha", "trabalhou bem", "trabalha bem", "vale o que ganha", "e confiavel", "e honesto",
  "bom politico", "mau politico", "mentiroso", "quem e o melhor", "quem e o pior",
];

export const PALAVRAS_SAUDACAO = [
  "oi", "ola", "ajuda", "ajudar", "o que voce faz", "o que voce sabe", "quem e voce", "bom dia",
  "boa tarde", "boa noite", "e ai", "comecar", "menu", "como usar voce", "tudo bem", "oie", "opa",
  "o que posso perguntar", "o que da para perguntar", "exemplos", "help", "hello", "hey", "eae",
];

/** Palavras sem peso para achar o nome de uma pessoa. */
export const PALAVRAS_VAZIAS = [
  "a", "o", "as", "os", "um", "uma", "ou", "que", "qual", "quais", "quanto", "quantos", "quantas",
  "como", "onde", "quando", "por", "para", "pra", "com", "sem", "em", "no", "na", "nos", "nas", "ao",
  "dele", "dela", "deles", "delas", "ele", "ela", "eles", "elas", "isso", "esse", "essa", "este", "esta",
  "foi", "fez", "teve", "tem", "tinha", "ter", "ser", "estao", "sao", "ja", "mais", "menos",
  "muito", "pouco", "me", "meu", "minha", "te", "voce", "vc", "voces", "eu", "sobre", "favor", "gostaria",
  "queria", "quero", "saber", "diga", "fale", "mostre", "mostra", "pode", "poderia", "ano",
  "deputado", "deputada", "deputados", "senador", "senadora", "senadores", "vereador", "vereadora",
  "parlamentar", "parlamentares", "prefeito", "prefeita", "governador", "governadora", "presidente",
  "dr", "dra", "tudo", "bem", "obrigado", "obrigada", "valeu", "ai", "hoje", "agora", "atual",
  "ultimo", "ultima", "sempre", "alguem", "algum", "alguma", "ver", "veja", "dado", "dados",
  "informacao", "informacoes", "pessoa", "politico", "politica", "politicos", "casa", "camara",
  "senado", "federal", "estadual", "municipal", "mandato", "mandatos", "2024", "2025", "2026",
  // Instituições e lugares genéricos: nunca são nome de pessoa.
  "governo", "governos", "governar", "uniao", "ministerio", "ministerios", "ministro", "ministra",
  "prefeitura", "prefeituras", "assembleia", "estado", "estados", "municipio", "municipios", "cidade",
  "cidades", "pais", "brasil", "brasileiro", "brasileira", "planalto", "congresso", "executivo",
  "legislativo", "judiciario", "poder", "orgao", "orgaos", "publico", "publica", "publicos",
  // Tempo e conversa.
  "mes", "meses", "passado", "passada", "neste", "nesse", "nessa", "nesta", "ontem", "semana", "dia",
  "dias", "hora", "aqui", "ali", "la", "ca", "so", "tambem", "porque", "pq", "oq", "q", "vcs", "nao",
  "sim", "faz", "fazer", "fazem", "feito", "tinha", "tenho", "ta", "to", "tava", "esta", "estao",
  "gostaria", "preciso", "precisava", "quer", "queremos", "vai", "vao", "ir", "foi", "fui", "quem",
  "oque", "cade", "alguns", "algumas", "todos", "todas", "todo", "toda", "cada", "outro", "outra",
  "entre", "dois", "duas", "tres", "quatro", "varios", "varias", "mesmo", "mesma", "mim", "nos", "gente", "povo", "cidadao", "cidadaos", "lista", "comparar",
  "dinheiro", "valor", "valores", "total", "numero", "numeros", "quantia", "reais", "real",
];

/** Palavras que ligam partes de um nome ("Maria do Rosário") e só contam no meio dele. */
export const CONECTORES_DE_NOME = ["de", "da", "do", "dos", "das", "e"];

/** Palavras genéricas: um resultado da busca que só casa com elas não é a pessoa pedida. */
export const PALAVRAS_GENERICAS = new Set([
  "governo", "governos", "uniao", "prefeitura", "estado", "municipio", "cidade", "camara", "senado",
  "assembleia", "federal", "estadual", "municipal", "presidente", "governador", "prefeito", "brasil",
  "ministerio", "partido", "novo", "nova", "povo", "social", "democrata", "popular", "nacional",
]);

/**
 * Palavras que o Argos reconhece em parte (sem entender a frase inteira) e o botão que
 * sugerimos nesse caso.
 */
export const SUGESTOES_POR_PALAVRA: { palavras: string[]; botao: Botao }[] = [
  { palavras: ["deputado", "deputados", "deputada", "senador", "senadores", "parlamentar", "parlamentares", "congresso"], botao: { rotulo: "Quem me representa?", frase: "quem me representa?" } },
  { palavras: ["deputado", "deputados", "deputada", "senador", "senadores", "parlamentar", "parlamentares"], botao: { rotulo: "Comparar parlamentares", frase: "como comparar parlamentares?" } },
  { palavras: ["governo", "uniao", "federal", "presidente", "ministerio", "imposto", "dinheiro", "verba", "orcamento"], botao: { rotulo: "Impostos e repasses", frase: "impostos e repasses" } },
  { palavras: ["partido", "partidos", "eleicao", "eleicoes", "voto", "votos", "votar", "campanha"], botao: { rotulo: "Dinheiro dos partidos", frase: "dinheiro dos partidos" } },
  { palavras: ["prefeito", "prefeitura", "vereador", "vereadores", "cidade", "municipio", "camara"], botao: { rotulo: "Quem me representa?", frase: "quem me representa?" } },
  { palavras: ["lei", "leis", "projeto", "projetos", "votacao", "votacoes", "plenario"], botao: { rotulo: "Projetos e votações", frase: "o que esta sendo votado" } },
  { palavras: ["site", "dados", "fonte", "fontes", "numero", "numeros", "confiar", "confiavel"], botao: { rotulo: "De onde vêm os dados?", frase: "De onde vêm os dados?" } },
];

export const TEXTOS = {
  apresentacao:
    "Eu sou o Argos. Não sou uma inteligência artificial: sou um assistente de respostas prontas. Procuro nos dados oficiais do site o que você perguntar sobre quem te representa, gastos, presença, projetos, dinheiro federal, partidos e como o site funciona, e respondo sempre com a fonte e a data. Não dou opinião nem nota.",
  opiniao: "Eu não dou opinião nem nota. Mostro o dado oficial para você tirar suas conclusões.",
  naoEntendi: "Não entendi. Tente assim:",
  pedirCep:
    "Para saber quem representa você, digite o seu CEP (8 números). Ele é usado só para achar a cidade e o estado e não é guardado.",
  pedirNome:
    "De quem? Escreva o nome de um deputado federal ou senador, por exemplo: quanto Fulano gastou.",
  semNome: "Não achei ninguém com esse nome.",
  semResumo:
    "Os resumos com número que eu sei contar são só de deputados federais e senadores. O perfil tem tudo o que o site mostra dessa pessoa, com fonte e data:",
  erroRede: "Não consegui buscar os dados agora. Tente de novo em instantes.",
};

/** Sugestões que aparecem na apresentação e quando o Argos não entende. */
export const EXEMPLOS = [
  "Quem me representa?",
  "Comparar dois deputados",
  "Impostos e repasses",
  "O que é a média da Casa?",
  "O site guarda o meu CEP?",
  "De onde vêm os dados?",
];
