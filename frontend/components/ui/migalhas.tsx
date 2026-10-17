import Link from "next/link";

/** Migalhas de pão: "Início / Partidos / PT". O último item é a página atual (sem link). */
export function Migalhas({ itens }: { itens: { rotulo: string; href?: string }[] }) {
  return (
    <nav aria-label="Você está em" className="text-sm text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-x-2">
        {itens.map((item, i) => {
          const ultimo = i === itens.length - 1;
          return (
            <li key={item.rotulo} className="flex items-center gap-2">
              {item.href && !ultimo ? (
                <Link href={item.href} className="alvo-link underline underline-offset-4 hover:text-foreground">
                  {item.rotulo}
                </Link>
              ) : (
                <span aria-current={ultimo ? "page" : undefined} className="min-w-0 break-words">
                  {item.rotulo}
                </span>
              )}
              {!ultimo && <span aria-hidden>/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
