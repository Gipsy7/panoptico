import type { Metadata } from "next";
import Link from "next/link";

import { OlhosApoiadores } from "@/components/olhos-apoiadores";
import { APOIADORES } from "@/lib/apoiadores";

export const metadata: Metadata = {
  title: "Apoiadores",
  description: "Quem ajudou a fazer o Panóptico existir: no código, nas ideias, nos testes ou com doações.",
};

export default function ApoiadoresPage() {
  const nomes = [...APOIADORES].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  return (
    <article className="pagina-secoes">
      <header className="flex flex-col gap-2">
        <p className="sobretitulo">Apoiadores</p>
        <h1 className="titulo-pagina">Cada olho é alguém que ajuda</h1>
        <p className="text-muted-foreground">
          Obrigado a quem ajudou a fazer o Panóptico existir: no código, nas ideias, nos testes,
          na divulgação ou com doações. No desenho, a torre do centro é o poder, e cada olho em volta,
          observando a torre, é uma dessas pessoas.
        </p>
      </header>

      <section aria-labelledby="lista-titulo" className="-mt-4 flex flex-col gap-4 md:-mt-10">
        <h2 id="lista-titulo" className="sr-only">
          Nomes publicados
        </h2>
        {nomes.length === 0 ? (
          <p className="text-muted-foreground">Ainda não há nomes publicados.</p>
        ) : (
          <>
            <OlhosApoiadores apoiadores={nomes} />
            <p className="text-sm text-muted-foreground">
              {nomes.length} {nomes.length === 1 ? "nome publicado" : "nomes publicados"}, em ordem alfabética.
            </p>
          </>
        )}
      </section>

      <section className="nota flex flex-col gap-2">
        <h2 className="text-lg">Quer apoiar?</h2>
        <p className="text-sm text-muted-foreground">
          A página{" "}
          <Link href="/apoie" className="underline underline-offset-2">
            Apoie
          </Link>{" "}
          mostra quanto custa manter o site e como doar. Se você ajudou de outro jeito e quer o seu nome aqui, ou doou e quer aparecer, é só autorizar por e-mail.
        </p>
      </section>
    </article>
  );
}
