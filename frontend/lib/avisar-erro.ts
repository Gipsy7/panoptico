/**
 * "Avisar erro" e "Sou a pessoa deste perfil" (Frente 7). Lógica pura: tipos, textos, validação
 * e montagem do corpo do POST /sugestoes. A gaveta está em components/avisar-erro/.
 */

export type TipoAviso = "erro" | "resposta";
export type CategoriaErro = "numero" | "cadastro" | "foto" | "link" | "outro";
export type Confirmacao = "email_funcional" | "oficio";
export type PerfilTipo = "parlamentar" | "deputado-estadual" | "vereador" | "eleito";

export const LIMITES = {
  textoMin: 10,
  erroMax: 2000,
  respostaMax: 3000,
  contatoMax: 200,
  secaoMax: 120,
} as const;

/** Tipos de erro, na ordem em que aparecem no primeiro passo. */
export const CATEGORIAS: { id: CategoriaErro; rotulo: string; apoio: string }[] = [
  { id: "numero", rotulo: "Um número", apoio: "diferente do que a fonte oficial mostra" },
  { id: "cadastro", rotulo: "Nome, partido ou cargo", apoio: "errado ou desatualizado" },
  { id: "foto", rotulo: "A foto", apoio: "de outra pessoa ou antiga" },
  { id: "link", rotulo: "Um link", apoio: "quebrado ou para o lugar errado" },
  { id: "outro", rotulo: "Outra coisa", apoio: "texto, data, explicação" },
];

export const CONFIRMACOES: { id: Confirmacao; rotulo: string; apoio: string }[] = [
  { id: "email_funcional", rotulo: "E-mail funcional da Casa", apoio: "escrevemos para o endereço oficial do gabinete" },
  { id: "oficio", rotulo: "Ofício do gabinete", apoio: "documento enviado pelo canal oficial" },
];

export const TEXTO_APAGAMENTO = "O contato serve só para responder. Apagamos em 180 dias e não guardamos o seu IP.";
export const TEXTO_REVISAO = "Nada muda no site sem uma pessoa conferir com a fonte oficial.";

export type Rascunho = {
  tipo: TipoAviso;
  categoria: CategoriaErro | null;
  texto: string;
  contato: string;
  confirmacao: Confirmacao | null;
  /** Título da seção da página, ou `null` para o perfil inteiro. */
  secao: string | null;
};

export type ContextoAviso = {
  /** Caminho da página (ex.: "/parlamentar/12"). */
  pagina: string;
  perfilTipo: PerfilTipo | null;
  perfilId: string | null;
};

export type CorpoSugestao = {
  tipo: TipoAviso;
  categoria: CategoriaErro | null;
  texto: string;
  pagina: string;
  secao: string | null;
  perfil_tipo: PerfilTipo | null;
  perfil_id: string | null;
  contato: string | null;
  confirmacao: Confirmacao | null;
};

export function limiteTexto(tipo: TipoAviso): number {
  return tipo === "resposta" ? LIMITES.respostaMax : LIMITES.erroMax;
}

/** Mensagem de erro do campo de texto, ou `null` se está certo. */
export function validarTexto(tipo: TipoAviso, texto: string): string | null {
  const t = texto.trim();
  if (t.length < LIMITES.textoMin) {
    return `Escreva um pouco mais: pelo menos ${LIMITES.textoMin} letras, para a pessoa que confere entender.`;
  }
  const max = limiteTexto(tipo);
  if (t.length > max) return `O texto passou de ${max} letras. Encurte um pouco.`;
  return null;
}

/** No pedido de resposta o contato é necessário (é por ele que se confirma a identidade). */
export function validarContato(tipo: TipoAviso, contato: string): string | null {
  const c = contato.trim();
  if (c.length > LIMITES.contatoMax) return `O contato passou de ${LIMITES.contatoMax} letras.`;
  if (tipo === "resposta" && c.length === 0) {
    return "Informe um e-mail ou telefone para a gente confirmar quem está pedindo.";
  }
  return null;
}

export function validarConfirmacao(tipo: TipoAviso, confirmacao: Confirmacao | null): string | null {
  if (tipo === "resposta" && !confirmacao) return "Escolha como a identidade será confirmada.";
  return null;
}

export function montarCorpo(r: Rascunho, ctx: ContextoAviso): CorpoSugestao {
  const contato = r.contato.trim();
  const secao = r.secao?.trim().slice(0, LIMITES.secaoMax) || null;
  return {
    tipo: r.tipo,
    categoria: r.tipo === "erro" ? (r.categoria ?? "outro") : null,
    texto: r.texto.trim(),
    pagina: ctx.pagina,
    secao,
    perfil_tipo: ctx.perfilTipo,
    perfil_id: ctx.perfilId,
    contato: contato ? contato : null,
    confirmacao: r.tipo === "resposta" ? r.confirmacao : null,
  };
}

/** Mensagem amigável para o que a API devolveu. */
export function mensagemDeFalha(status: number, detalhe?: string): string {
  if (status === 429) {
    return "Você já mandou vários avisos nesta hora. Espere um pouco e tente de novo; o texto que você escreveu continua aqui.";
  }
  if (status === 422) return "Algum campo não passou na conferência. Releia o texto e tente de novo.";
  if (status === 404 || status === 503 || status === 0) {
    return "Não foi possível enviar agora. O texto continua aqui; tente de novo daqui a pouco.";
  }
  return detalhe && detalhe.length < 200 ? detalhe : "Não foi possível enviar agora. Tente de novo daqui a pouco.";
}

/** Texto de seção para comparar (sem acento, minúsculo, sem espaços repetidos). */
export function normalizarSecao(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/** Âncora usada no link "há uma resposta" e no bloco de respostas. */
export const ANCORA_RESPOSTAS = "respostas-de-quem-e-citado";
