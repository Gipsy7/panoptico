import { EH_RELEASE, SITE_OFICIAL } from "@/lib/site";

/**
 * Aviso no topo do release (homologação em release.panoptico.social.br). Só aparece quando o build
 * tem NEXT_PUBLIC_AMBIENTE=release; na produção não gera nada.
 */
export function FaixaRelease() {
  if (!EH_RELEASE) return null;
  return (
    <p className="border-b border-border/70 bg-secondary px-4 py-1.5 text-center text-xs leading-snug text-secondary-foreground">
      Versão de teste — o site oficial é{" "}
      <a href={SITE_OFICIAL} className="font-medium underline underline-offset-2 hover:text-foreground">
        panoptico.social.br
      </a>
    </p>
  );
}
