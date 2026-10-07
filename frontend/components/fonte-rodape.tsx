import { formatarData } from "@/lib/formato";

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
    <p className="text-xs text-muted-foreground">
      Fonte:{" "}
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
          {fonte}
        </a>
      ) : (
        fonte
      )}
      {atualizadoEm && <> · atualizado em {formatarData(atualizadoEm)}</>}
    </p>
  );
}
