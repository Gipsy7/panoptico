/** Tipos compartilhados do Argos (chat de respostas prontas). */

export type AssuntoDado = "gastos" | "presenca" | "projetos" | "emendas" | "representantes";

export type Assunto = AssuntoDado | "pessoa" | "ranking" | "site" | "opiniao" | "saudacao" | "nenhum";

/** Assuntos que se perguntam sobre uma pessoa. */
export type AssuntoPessoa = "gastos" | "presenca" | "projetos" | "emendas" | "pessoa";

export type Interpretacao = {
  assunto: Assunto;
  /** CEP com 8 dígitos e traço ("88340-000"). */
  cep?: string;
  /** O que sobrou da frase depois de tirar palavras-chave e palavras vazias. */
  nome?: string;
  /** Para `site`: qual pergunta de /perguntas responde ("sobre" = apresentação geral). */
  perguntaId?: string;
};

/** A pessoa de quem se está falando; fica só na tela, nunca é gravada. */
export type PessoaLembrada = {
  nome: string;
  /** Endereço do perfil no site. */
  caminho: string;
};

export type Acao = { assunto: AssuntoPessoa; pessoa: PessoaLembrada };

export type Botao = {
  rotulo: string;
  /** Frase que aparece como se a pessoa tivesse escrito. */
  frase: string;
  /** Quando presente, o clique não passa pela interpretação: vai direto a esta ação. */
  acao?: Acao;
};

export type LinkResposta = { rotulo: string; href: string };

export type Mensagem = {
  texto: string;
  /** Linhas de apoio (por exemplo, a média da Casa), uma por parágrafo. */
  detalhes?: string[];
  links: LinkResposta[];
  botoes: Botao[];
  fonte?: { nome: string; url?: string; atualizadoEm?: string | null };
  /** Erro de rede ou da API: o chat pode destacar. */
  erro?: boolean;
};

export type Contexto = { pessoa?: PessoaLembrada };
