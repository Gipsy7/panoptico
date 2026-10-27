import { formatarData } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

export function FonteRodape({
  fonte,
  url,
  atualizadoEm,
}: {
  fonte: string;
  url?: string;
  atualizadoEm?: string | null;
}) {
  return (
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
  );
}
