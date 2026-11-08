import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Titular e vice lado a lado: no Executivo os dois são eleitos juntos, na mesma chapa, e o vice
 * assume se o titular sair. Serve em servidor e cliente (sem estado); o retrato vem de fora porque
 * cada tela tem o seu (FotoOuIniciais no perfil, Retrato no painel dos prédios).
 */
export type PessoaDaChapa = {
  nome: string;
  partido: string | null;
  cargo: string;
  href: string | null;
  retrato: ReactNode;
};

/** "Prefeito" → "Vice-prefeito"; já vindo com "Vice", fica como está. */
export function cargoDoVice(cargo: string): string {
  return /^vice/i.test(cargo) ? cargo : `Vice-${cargo.toLowerCase()}`;
}

function Pessoa({ p }: { p: PessoaDaChapa }) {
  const corpo = (
    <>
      {p.retrato}
      <span className="min-w-0">
        <span className="block text-xs tracking-wide text-muted-foreground uppercase">{p.cargo}</span>
        <span className="block font-semibold [overflow-wrap:anywhere] group-hover:underline">{p.nome}</span>
        {p.partido && <span className="block text-sm text-muted-foreground">{p.partido}</span>}
      </span>
    </>
  );
  const classes = "group flex min-h-11 items-start gap-2.5 py-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze";
  return p.href ? (
    <Link href={p.href} className={`${classes} hover:opacity-85`}>
      {corpo}
    </Link>
  ) : (
    <div className={classes}>{corpo}</div>
  );
}

export function Chapa({ titular, vice, rodape }: { titular: PessoaDaChapa; vice: PessoaDaChapa | null; rodape?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="grid grid-cols-2 gap-x-3 [&>*+*]:border-l [&>*+*]:border-border [&>*+*]:pl-3">
        <Pessoa p={titular} />
        {vice ? (
          <Pessoa p={vice} />
        ) : (
          <p className="py-2 text-sm text-muted-foreground">Sem vice registrado no TSE.</p>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{rodape ?? "Eleitos juntos, na mesma chapa."}</p>
    </div>
  );
}
