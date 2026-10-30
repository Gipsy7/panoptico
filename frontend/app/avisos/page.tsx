import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AvisosAparelho } from "@/components/avisos-aparelho";
import { AVISOS_LIGADOS } from "@/lib/avisos-config";

// Página pessoal de cada aparelho: fora dos buscadores e do mapa do site.
export const metadata: Metadata = {
  title: "Avisos neste aparelho",
  description: "O que este aparelho acompanha e as novidades recentes.",
  robots: { index: false, follow: false },
};

export default function AvisosPage() {
  // Sem a chave pública do build, o recurso está desligado e a página não existe.
  if (!AVISOS_LIGADOS) notFound();
  return (
    <article className="pagina-secoes">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Avisos no celular</p>
        <h1 className="titulo-pagina">Avisos neste aparelho</h1>
        <p className="max-w-prose text-muted-foreground">
          O que este aparelho acompanha e as novidades dos últimos dias. Nada aqui depende de cadastro.
        </p>
      </header>
      <AvisosAparelho />
    </article>
  );
}
