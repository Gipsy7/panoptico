import Link from "next/link";

import { getAgendaSegundoTurno } from "@/lib/api";
import { formatarData } from "@/lib/formato";

/**
 * Link discreto para o comparador do 2º turno. Só aparece enquanto há 2º turno por
 * disputar (a API decide pela data da eleição) e, com `uf`, só se houver disputa que valha
 * para o estado (presidente ou governador). Some sozinho depois do 2º turno.
 */
export async function AvisoSegundoTurno({ uf, href }: { uf?: string; href: string }) {
  const r = await getAgendaSegundoTurno();
  if (!r.ok || !r.dados.em_andamento) return null;
  const a = r.dados;
  const governador = uf ? a.ufs_governador.includes(uf) : a.ufs_governador.length > 0;
  if (!a.presidente && !governador) return null;
  const cargos = [a.presidente ? "presidente" : null, governador ? "governador" : null].filter(Boolean).join(" e ");
  return (
    <Link
      href={href}
      className="group flex min-h-11 flex-col gap-0.5 border-l-2 border-bronze py-1 pl-3 transition-colors duration-200 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
    >
      <span className="sobretitulo">
        2º turno{a.data_segundo_turno ? ` · ${formatarData(a.data_segundo_turno)}` : ""}
      </span>
      <span className="font-medium group-hover:underline group-hover:underline-offset-4">
        Compare os candidatos a {cargos}, lado a lado ›
      </span>
    </Link>
  );
}
