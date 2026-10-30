/**
 * Vocabulário do Argos: é este arquivo que se edita para ensiná-lo.
 *
 * Tudo aqui está sem acento, em minúsculas e sem pontuação (a frase é normalizada do mesmo
 * jeito antes de comparar). Frase com mais de uma palavra vale mais pontos que palavra solta.
 */
import type { AssuntoDado } from "./tipos";

/** Palavras e frases que indicam cada assunto de dado. */
export const PALAVRAS_DADO: Record<AssuntoDado, string[]> = {
  gastos: [
    "gasto", "gastos", "gastou", "gastar", "gastaram", "cota", "cotas", "despesa", "despesas",
    "reembolso", "reembolsos", "dinheiro", "custa", "custou", "gabinete", "ceap",
    "verba de gabinete", "quanto custa",
  ],
  presenca: [
    "presenca", "presencas", "faltou", "faltas", "falta", "votou", "votacao", "votacoes",
    "compareceu", "ausente", "ausencia", "ausencias",
  ],
  projetos: [
    "projeto", "projetos", "lei", "leis", "propos", "propoe", "proposta", "propostas", "autor",
    "autoria", "apresentou", "projeto de lei", "pl",
  ],
  emendas: [
    "emenda", "emendas", "verba", "verbas", "mandou dinheiro", "enviou dinheiro",
    "destinou dinheiro", "destinou", "dinheiro para a cidade",
  ],
  representantes: [
    "cep", "moro", "minha cidade", "quem me representa", "meus deputados", "meu deputado",
    "meus senadores", "meus representantes", "quem sao meus", "minha regiao", "meu estado",
    "representante", "representantes",
  ],
};

/** Ordem de desempate entre assuntos de dado com a mesma pontuação. */
export const ORDEM_DADO: AssuntoDado[] = ["gastos", "presenca", "projetos", "emendas", "representantes"];

/** Quem pede opinião ou nota. Vem antes de tudo: o Argos nunca opina. */
export const PALAVRAS_OPINIAO = [
  "em quem votar", "em quem voto", "em quem eu voto", "em quem devo votar", "em quem vou votar",
  "quem devo votar", "vale a pena votar", "corrupto", "corrupta", "corrupcao", "ladrao", "ladra",
  "presta", "nao presta", "e bom", "e boa", "e ruim", "bom deputado", "bom senador", "mau deputado",
  "melhor", "pior", "honesto", "honesta", "confiar", "recomenda", "recomendar", "merece",
];

export const PALAVRAS_SAUDACAO = [
  "oi", "ola", "ajuda", "ajudar", "o que voce faz", "o que voce sabe", "quem e voce", "bom dia",
  "boa tarde", "boa noite", "e ai", "comecar", "menu", "como usar voce", "tudo bem",
];

/** Dúvidas sobre o site. `id` é o de `PERGUNTAS_FREQUENTES` ("sobre" = apresentação geral). */
export type FraseSite = { id: string; frases: string[] };

export const PALAVRAS_SITE: FraseSite[] = [
  { id: "fonte", frases: ["de onde vem", "de onde vem os dados", "fonte", "fontes", "origem dos dados", "dados oficiais"] },
  {
    id: "frequencia",
    frases: ["atualizado", "atualiza", "atualizacao", "com que frequencia", "quando atualiza", "desatualizado", "dados antigos"],
  },
  {
    id: "cobertura",
    frases: ["nao aparece", "nao aparecem", "nao encontrei", "nao tem vereador", "cobertura", "minha camara"],
  },
  {
    id: "cep",
    frases: [
      "guarda meu cep", "guarda o cep", "guardam meu cep", "guarda minha localizacao", "grava meu cep",
      "salva meu cep", "privacidade", "lgpd", "cookies", "rastreia", "meus dados",
    ],
  },
  {
    id: "nota",
    frases: ["da nota", "dar nota", "nota ou ranking", "ranking", "ligado a partido", "e de algum partido", "imparcial", "neutro"],
  },
  { id: "media-casa", frases: ["media da casa", "media da camara", "media do senado", "media"] },
  { id: "erro", frases: ["numero errado", "numero diferente", "errado", "corrigir", "erro", "reportar", "bug"] },
  {
    id: "quem-paga",
    frases: ["quem paga", "quem faz", "quem mantem", "quem financia", "quem criou", "patrocinio", "doacao", "doacoes"],
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
];

/** Palavras que ligam partes de um nome ("Maria do Rosário") e só contam no meio dele. */
export const CONECTORES_DE_NOME = ["de", "da", "do", "dos", "das", "e"];

export const TEXTOS = {
  apresentacao:
    "Eu sou o Argos. Não sou uma inteligência artificial: sou um assistente de respostas prontas. Procuro nos dados oficiais do site o que você perguntar sobre deputados federais e senadores e respondo sempre com a fonte e a data. Não dou opinião nem nota.",
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
  "O que é a média da Casa?",
  "O site guarda o meu CEP?",
  "De onde vêm os dados?",
];
