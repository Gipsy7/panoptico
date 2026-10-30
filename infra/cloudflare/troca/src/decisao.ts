export type Modo = "auto" | "principal" | "reserva" | "observar";
export type Destino = "principal" | "reserva";

export interface EstadoServico {
  ativo: Destino;
  falhas: number;
  sucessos: number;
  modo: Modo;
}

// 3 minutos seguidos fora do ar: uma troca de contêiner (segundos) não dispara a reserva.
export const FALHAS_PARA_RESERVA = 3;
export const SUCESSOS_PARA_VOLTAR = 10;
export const TIMEOUT_MS = 8000;

export function estadoInicial(): EstadoServico {
  return { ativo: "principal", falhas: 0, sucessos: 0, modo: "auto" };
}

export interface Resposta {
  timeout?: boolean;
  status?: number;
  corpo?: string;
}

/** Diz se a resposta de um teste conta como saudavel. */
export function respostaSaudavel(r: Resposta, ehApi = false): boolean {
  if (r.timeout || r.status === undefined) return false;
  const corpo = r.corpo ?? "";
  if (r.status >= 500 || r.status === 402) return false;
  if (r.status === 403 && /DEPLOYMENT_DISABLED|Payment required/i.test(corpo)) return false;
  if (ehApi) {
    if (r.status < 200 || r.status >= 300) return false;
    try {
      const j = JSON.parse(corpo) as { banco?: string };
      if (j.banco !== "ok") return false;
    } catch {
      return false;
    }
  }
  return true;
}

export interface Decisao {
  estado: EstadoServico;
  /** Destino para o qual o DNS deve ir agora, ou null se nada muda. */
  trocarPara: Destino | null;
  /** Em modo observar: o que faria, sem fazer. */
  observou: Destino | null;
}

/**
 * Atualiza contadores com o teste da principal e decide.
 * `reservaSaudavel` so importa para ir a reserva.
 */
export function decidir(
  anterior: EstadoServico,
  principalOk: boolean,
  reservaSaudavel: boolean,
): Decisao {
  const e: EstadoServico = { ...anterior };
  if (principalOk) {
    // Teto nos contadores: com a origem estável o estado não muda e o KV não é regravado
    // (o plano grátis permite 1.000 gravações por dia; o cron roda 1.440 vezes).
    e.sucessos = Math.min(e.sucessos + 1, SUCESSOS_PARA_VOLTAR);
    e.falhas = 0;
  } else {
    e.falhas = Math.min(e.falhas + 1, FALHAS_PARA_RESERVA);
    e.sucessos = 0;
  }

  let alvo: Destino = e.ativo;
  if (e.modo === "principal" || e.modo === "reserva") {
    alvo = e.modo;
  } else if (e.ativo === "principal") {
    if (e.falhas >= FALHAS_PARA_RESERVA && reservaSaudavel) alvo = "reserva";
  } else if (e.sucessos >= SUCESSOS_PARA_VOLTAR) {
    alvo = "principal";
  }

  if (alvo === e.ativo) return { estado: e, trocarPara: null, observou: null };

  if (e.modo === "observar") return { estado: e, trocarPara: null, observou: alvo };

  e.ativo = alvo;
  e.falhas = 0;
  e.sucessos = 0;
  return { estado: e, trocarPara: alvo, observou: null };
}

/**
 * Endereços de release (homologação: release.panoptico.social.br, api-release...) nunca entram na
 * troca: nem como registro que o Worker muda, nem como teste de saúde. O release roda na mesma VPS,
 * com o mesmo banco, e não tem reserva. Recebe hostnames ou URLs; devolve os que são de release.
 */
export function enderecosDeRelease(valores: (string | undefined)[]): string[] {
  return valores.filter((v): v is string => {
    if (!v) return false;
    let host = v.trim().toLowerCase();
    try {
      if (host.includes("://")) host = new URL(host).hostname;
    } catch {
      return false;
    }
    return /(^|[.-])release[.-]/.test(host);
  });
}
