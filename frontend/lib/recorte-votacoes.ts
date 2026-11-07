/**
 * Textos do recorte "Só o que muda leis" (votações sobre o texto x de procedimento), usados em
 * /projetos (calendário) e no perfil. Regra em docs/DECISOES.md (2026-11-07, Frente 4).
 */
import type { ContagemTipos, RecorteVotacoes, Votos } from "@/lib/api";

const plural = (n: number, um: string, varios: string) => (n === 1 ? um : varios);

/** Parâmetro do endereço que desliga a chave (padrão: ligada, só sobre o texto). */
export const PARAM_RECORTE = "votacoes";

/** Recorte pedido a partir do endereço: ligada salvo `votacoes=todas`. */
export function recorteDoEndereco(valor: string | string[] | undefined): RecorteVotacoes {
  const v = Array.isArray(valor) ? valor[0] : valor;
  return v === "todas" ? "todas" : "merito";
}

/** "Mostrando 48 de 123 votações. As outras 75 são de procedimento (...)." */
export function avisoRecorte(c: ContagemTipos, tipo: RecorteVotacoes): string {
  if (c.todas === 0) return "Nenhuma votação nominal neste período.";
  if (tipo === "merito") {
    const inicio = `Mostrando ${c.merito} de ${c.todas} ${plural(c.todas, "votação", "votações")}.`;
    if (c.procedimento === 0) return `${inicio} Nenhuma é de procedimento.`;
    const fora =
      c.procedimento === 1
        ? "A outra é de procedimento"
        : `As outras ${c.procedimento} são de procedimento`;
    return `${inicio} ${fora} (urgência, adiamento, retirada de pauta).`;
  }
  if (tipo === "procedimento") {
    return `Mostrando ${c.procedimento} de ${c.todas} ${plural(c.todas, "votação", "votações")}, só as de procedimento.`;
  }
  return `Mostrando ${c.todas === 1 ? "a única votação" : `todas as ${c.todas} votações`}: ${c.merito} sobre o texto e ${c.procedimento} de procedimento.`;
}

/** Rótulo curto do recorte dos números ("Recorte: só as votações sobre o texto"). */
export function rotuloRecorte(tipo: RecorteVotacoes): string {
  if (tipo === "merito") return "só as votações sobre o texto";
  if (tipo === "procedimento") return "só as votações de procedimento";
  return "todas as votações, sobre o texto e de procedimento";
}

export const ROTULO_TIPO = { merito: "Sobre o texto", procedimento: "Procedimento" } as const;

/** Os números de alinhamento em todas as votações, para o resumo do topo e "Para entender os
 * números" (que não seguem a chave da seção "Como votou"). */
export function comNumerosDeTodas(v: Votos): Votos {
  return v.todas ? { ...v, ...v.todas, tipo: "todas" } : v;
}
