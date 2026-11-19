export type Modo = "auto" | "principal" | "reserva" | "observar";
export type Destino = "principal" | "reserva";

export interface EstadoServico {
  ativo: Destino;
  falhas: number;
  sucessos: number;
  modo: Modo;
  /** O dono foi avisado de que o serviço está fora e ainda não soube da volta. */
  alertado?: boolean;
  /** Quando saiu o último e-mail de queda (ms), para o intervalo mínimo entre eles. */
  ultimoAlerta?: number;
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

/** Intervalo mínimo entre dois e-mails de queda do mesmo serviço. */
export const INTERVALO_ALERTAS_MS = 60 * 60_000;

export type Evento = "foi_para_reserva" | "voltou_para_principal" | "parou_sem_troca" | "voltou_a_responder";

/**
 * O que avisar ao dono por e-mail depois de um teste. Segue o estado, não cada virada: com a VPS
 * oscilando (3 falhas, 1 sucesso, 3 falhas...) saíram 37 e-mails em 18/11/2026.
 * - Queda: o serviço está fora (na reserva ou com FALHAS_PARA_RESERVA falhas seguidas) e o dono
 *   ainda não sabe. No máximo um e-mail de queda por INTERVALO_ALERTAS_MS; se a queda continuar
 *   depois do intervalo sem aviso, o e-mail sai nessa hora.
 * - Volta: só para quem foi avisado da queda, e só com a principal estável (SUCESSOS_PARA_VOLTAR
 *   sucessos seguidos, que é também quando o DNS volta da reserva).
 * Devolve o evento e o estado com as marcas do aviso.
 */
export function alertar(d: Decisao, agora: number): { evento: Evento | null; estado: EstadoServico } {
  const e = { ...d.estado };
  const fora = e.ativo === "reserva" || e.falhas >= FALHAS_PARA_RESERVA;
  const estavel = d.trocarPara === "principal" || (e.ativo === "principal" && e.sucessos >= SUCESSOS_PARA_VOLTAR);
  if (fora && !e.alertado) {
    if (e.ultimoAlerta !== undefined && agora - e.ultimoAlerta < INTERVALO_ALERTAS_MS) return { evento: null, estado: e };
    e.alertado = true;
    e.ultimoAlerta = agora;
    return { evento: e.ativo === "reserva" ? "foi_para_reserva" : "parou_sem_troca", estado: e };
  }
  if (estavel && e.alertado) {
    e.alertado = false;
    return { evento: d.trocarPara === "principal" ? "voltou_para_principal" : "voltou_a_responder", estado: e };
  }
  return { evento: null, estado: e };
}
