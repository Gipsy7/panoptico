/** Tipos compartilhados do Argos (chat de respostas prontas). */

export type Assunto =
  | "gastos"
  | "presenca"
  | "projetos"
  | "emendas"
  | "representantes"
  | "comparar"
  | "dinheiro_federal"
  | "partidos"
  | "lista"
  | "cidade"
  | "eleicao"
  | "salario"
  | "executivo"
  | "projetos_busca"
  | "governo_gasto"
  | "secao"
  | "pagina"
  | "pessoa"
  | "ranking"
  | "site"
  | "opiniao"
  | "saudacao"
  | "nenhum";

/** Assuntos que se perguntam sobre uma pessoa. */
export type AssuntoPessoa = "gastos" | "presenca" | "projetos" | "emendas" | "salario" | "secao" | "pessoa";

export type CriterioLista = "gastos" | "presenca" | "projetos" | "emendas";

export type Interpretacao = {
  assunto: Assunto;
  /** CEP com 8 dígitos e traço ("88340-000"). */
  cep?: string;
  /** O que sobrou da frase depois de tirar palavras-chave, entidades e palavras vazias. */
  nome?: string;
  /** Para `comparar`: um nome por pessoa. */
  nomes?: string[];
  /** Para `site`: qual pergunta de /perguntas responde ("sobre" = apresentação geral). */
  perguntaId?: string;
  uf?: string;
  partido?: string;
  ano?: number;
  mes?: number;
  /** Disse "esse mês", "este ano" ou "hoje". */
  relativo?: boolean;
  casa?: "camara" | "senado";
  /** Para `secao` e `pagina`: qual (ver `vocabulario.ts`). */
  secao?: string;
  /** Para `projetos_busca`: o tema. */
  tema?: string;
  /** Para `ranking`. */
  ordem?: { criterio: CriterioLista; desc: boolean };
  /** Para `governo_gasto` e `executivo`. */
  instituicao?: "federal" | "estadual" | "municipal";
  cargo?: "presidente" | "governador" | "prefeito";
  /** Para `nenhum`: botões ligados às palavras que o Argos reconheceu em parte. */
  sugestoes?: Botao[];
};

/** A pessoa de quem se está falando; fica só na tela, nunca é gravada. */
export type PessoaLembrada = {
  nome: string;
  /** Endereço do perfil no site. */
  caminho: string;
};

export type Acao = {
  assunto: AssuntoPessoa;
  pessoa: PessoaLembrada;
  secao?: string;
  ano?: number;
  mes?: number;
};

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
