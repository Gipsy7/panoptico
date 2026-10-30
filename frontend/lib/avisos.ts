/**
 * Avisos no celular (Web Push): lógica pura, sem tocar no navegador. As APIs do navegador e a rede
 * entram pelos argumentos, para testar sem nada disso. A fonte da verdade do aparelho é a inscrição
 * do próprio navegador (PushSubscription); o site não guarda nada em cookie nem em localStorage.
 */

export type EstadoAviso = "sem-suporte" | "pronto" | "pedindo" | "ativo" | "negado" | "erro";

/** Por que o aparelho pode (ou não) receber avisos. */
export type Suporte = "suportado" | "ios-instalar" | "app-interno" | "sem-suporte";

export type PermissaoAviso = "default" | "granted" | "denied" | "indisponivel";

export type AlvoTipo = "parlamentar" | "projeto";

/** Frase que vale para o botão e para a página /avisos: o que é avisado e o que é guardado. */
export const TEXTO_O_QUE_AVISA =
  "Se você ativar, mandamos no máximo 1 aviso por dia, com votos, andamento de projetos e registros oficiais de quem você acompanha. Gastos, emendas e dados da cidade não entram nos avisos.";

export const TEXTO_O_QUE_GUARDA =
  "Guardamos só um endereço técnico do aparelho e o que ele acompanha; nunca nome, telefone nem e-mail. Você cancela quando quiser, e o cancelamento apaga esses dados na hora.";

export type EntradaSuporte = {
  userAgent: string;
  plataforma?: string;
  pontosDeToque?: number;
  /** navigator.standalone (Safari do iPhone) ou display-mode: standalone. */
  instalado: boolean;
  temServiceWorker: boolean;
  temPushManager: boolean;
  temNotification: boolean;
};

function ehIos(e: EntradaSuporte): boolean {
  if (/iPad|iPhone|iPod/.test(e.userAgent)) return true;
  // iPad com "site para computador" se apresenta como Mac, mas tem tela de toque.
  return e.plataforma === "MacIntel" && (e.pontosDeToque ?? 0) > 1;
}

/** Navegadores embutidos em aplicativos (WhatsApp, Facebook, Instagram) costumam não ter avisos. */
function ehNavegadorInterno(userAgent: string): boolean {
  return /WhatsApp|FBAN|FBAV|Instagram|Line\/|; wv\)/i.test(userAgent);
}

export function detectarSuporte(e: EntradaSuporte): Suporte {
  const completo = e.temServiceWorker && e.temPushManager && e.temNotification;
  if (completo) return "suportado";
  // No iPhone, os avisos só existem para o site adicionado à tela inicial.
  if (ehIos(e) && !e.instalado) return "ios-instalar";
  if (ehNavegadorInterno(e.userAgent)) return "app-interno";
  return "sem-suporte";
}

/** Estado do botão ao carregar, antes de qualquer clique. `acompanha` vem da consulta ao servidor. */
export function estadoInicial(suporte: Suporte, permissao: PermissaoAviso, acompanha: boolean): EstadoAviso {
  if (suporte !== "suportado" || permissao === "indisponivel") return "sem-suporte";
  if (permissao === "denied") return "negado";
  if (permissao === "granted" && acompanha) return "ativo";
  return "pronto";
}

/** Chave do alvo na API: "<casa>:<id_externo>". Nulo se faltar um dos dois. */
export function chaveAlvo(casa: string | null | undefined, idExterno: string | number | null | undefined): string | null {
  if (!casa || idExterno === null || idExterno === undefined || String(idExterno).trim() === "") return null;
  return `${casa}:${String(idExterno).trim()}`;
}

/** Só caminhos do próprio site: nunca um endereço de fora vindo da resposta do servidor. */
export function caminhoSeguro(caminho: string | null | undefined): string | null {
  if (!caminho || !caminho.startsWith("/") || caminho.startsWith("//") || caminho.includes("\\")) return null;
  return caminho;
}

/** A chave pública VAPID chega em base64 "seguro para URL"; o navegador quer os bytes. */
export function chaveVapidParaBytes(base64Url: string): Uint8Array<ArrayBuffer> {
  const preenchida = base64Url.trim().replace(/-/g, "+").replace(/_/g, "/");
  const base64 = preenchida + "=".repeat((4 - (preenchida.length % 4)) % 4);
  const texto = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(texto.length));
  for (let i = 0; i < texto.length; i++) bytes[i] = texto.charCodeAt(i);
  return bytes;
}

type Assinatura = { endpoint: string; keys?: { p256dh?: string; auth?: string } };

export type CorpoIdentidade = { endpoint: string; auth: string };

/** Corpo de /avisos/inscrever; nulo se a inscrição do navegador vier incompleta. */
export function corpoInscricao(sub: Assinatura): { endpoint: string; p256dh: string; auth: string } | null {
  const { p256dh, auth } = sub.keys ?? {};
  if (!sub.endpoint || !p256dh || !auth) return null;
  return { endpoint: sub.endpoint, p256dh, auth };
}

export function identidade(sub: Assinatura): CorpoIdentidade | null {
  const auth = sub.keys?.auth;
  if (!sub.endpoint || !auth) return null;
  return { endpoint: sub.endpoint, auth };
}

export function corpoAlvo(
  id: CorpoIdentidade,
  alvoTipo: AlvoTipo,
  alvoChave: string,
  acao: "adicionar" | "remover",
) {
  return { ...id, alvo_tipo: alvoTipo, alvo_chave: alvoChave, acao };
}

// --- Chamadas à API (a rede entra pelo argumento `buscar`) ---

export type Buscar = (url: string, init: RequestInit) => Promise<Response>;

export type RespostaAviso<T> = { ok: true; dados: T } | { ok: false; status: number; mensagem: string };

export type AlvoAcompanhado = { alvo_tipo: AlvoTipo; alvo_chave: string; nome: string; caminho: string };
export type Novidade = { titulo: string; caminho: string; fonte: string; data_fato: string; detectado_em: string };
export type MinhasAvisos = { alvos: AlvoAcompanhado[]; novidades: Novidade[] };

/** O que mostrar para cada falha conhecida da API. */
export function mensagemDeFalha(status: number): string {
  if (status === 503) return "Os avisos não estão disponíveis agora.";
  if (status === 429) return "Muitos pedidos em pouco tempo. Tente de novo daqui a alguns minutos.";
  if (status === 404) return "Este aparelho não está mais cadastrado nos avisos.";
  if (status === 0) return "Sem conexão com o servidor. Confira a internet e tente de novo.";
  return "Não foi possível concluir. Tente de novo mais tarde.";
}

/** POST em JSON. Confere `response.ok`: nada de dar a escrita por feita sem a resposta do servidor. */
export async function postarAviso<T>(buscar: Buscar, base: string, caminho: string, corpo: unknown): Promise<RespostaAviso<T>> {
  let resposta: Response;
  try {
    resposta = await buscar(`${base}${caminho}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 0, mensagem: mensagemDeFalha(0) };
  }
  if (!resposta.ok) return { ok: false, status: resposta.status, mensagem: mensagemDeFalha(resposta.status) };
  try {
    return { ok: true, dados: (await resposta.json()) as T };
  } catch {
    return { ok: false, status: resposta.status, mensagem: mensagemDeFalha(resposta.status) };
  }
}

/** O aparelho já acompanha este alvo? Usa só o que o servidor devolveu. */
export function acompanhaAlvo(minhas: MinhasAvisos, alvoTipo: AlvoTipo, alvoChave: string): boolean {
  return (minhas.alvos ?? []).some((a) => a.alvo_tipo === alvoTipo && a.alvo_chave === alvoChave);
}

/** Texto de apoio do botão, conforme o motivo de não haver avisos. */
export function instrucaoSemSuporte(suporte: Exclude<Suporte, "suportado">): string {
  if (suporte === "ios-instalar") {
    return "No iPhone, os avisos só funcionam depois de adicionar o Panóptico à tela inicial: toque em Compartilhar e em “Adicionar à Tela de Início”, abra o Panóptico por lá e volte a esta página.";
  }
  if (suporte === "app-interno") {
    return "Este link foi aberto dentro de outro aplicativo, que pode não permitir avisos. Abra o endereço no navegador do celular (por exemplo, o Chrome) e tente de novo.";
  }
  return "Este navegador não permite avisos. Se o endereço foi aberto dentro de outro aplicativo, abra-o no navegador do celular.";
}
