import Link from "next/link";

import type { PerfilTipo } from "@/lib/avisar-erro";
import { getCorrecoes } from "@/lib/api";
import { destinoCorrecao, textoLinkCorrecao } from "@/lib/correcoes";

/** Link discreto no topo do perfil que teve correção; some se não teve (ou se a rota não responde). */
export async function LinkCorrecao({ tipo, id }: { tipo: PerfilTipo; id: string }) {
  const r = await getCorrecoes({ tipo, id });
  if (!r.ok || r.dados.total === 0) return null;
  return (
    <Link
      href={destinoCorrecao(r.dados.itens)}
      className="alvo-link self-start text-sm text-muted-foreground underline underline-offset-4"
    >
      {textoLinkCorrecao(r.dados.total)}
    </Link>
  );
}
