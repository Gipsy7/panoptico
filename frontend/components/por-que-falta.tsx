import Link from "next/link";

import { idDaCasa } from "@/lib/cobertura";

/**
 * Link neutro para explicar por que um dado não aparece.
 *
 * Uso, ao lado de um aviso "sem dado" numa seção:
 *   <PorQueFalta uf="PR" casa="ALPR" />
 * Leva a /sobre-as-fontes/cobertura?uf=PR#alpr, onde a situação da casa aparece igual
 * para todos os estados. `casa` é o nome da casa como na matriz de cobertura
 * ("ALPR", "Governo de PR", "Prefeituras de PR", "Câmara dos Deputados", "Senado Federal");
 * sem `casa`, o link vai ao topo do estado.
 */
export function PorQueFalta({ uf, casa }: { uf?: string | null; casa?: string }) {
  const params = uf ? `?uf=${encodeURIComponent(uf.toUpperCase())}` : "";
  const ancora = casa ? `#${idDaCasa(casa)}` : "";
  return (
    <Link
      href={`/sobre-as-fontes/cobertura${params}${ancora}`}
      className="text-sm text-muted-foreground underline underline-offset-2"
    >
      Por que falta este dado?
    </Link>
  );
}
