import { EntradaRodape } from "@/components/avisar-erro/entradas";
import { formatarData } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

export function FonteRodape({
  fonte,
  url,
  atualizadoEm,
  semAviso = false,
}: {
  fonte: string;
  url?: string;
  atualizadoEm?: string | null;
  /** Sem a entrada "Achou um erro neste número?" (que só aparece dentro de um perfil). */
  semAviso?: boolean;
}) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">
        Fonte:{" "}
        {url ? (
          <LinkExterno href={url} className="underline underline-offset-2">
            {fonte}
          </LinkExterno>
        ) : (
          fonte
        )}
        {atualizadoEm && <> · atualizado em {formatarData(atualizadoEm)}</>}
      </p>
      {!semAviso && <EntradaRodape />}
    </div>
  );
}
