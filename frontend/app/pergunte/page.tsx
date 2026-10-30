import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ArgosChat } from "@/components/argos/argos-chat";

export const metadata: Metadata = {
  title: "Pergunte ao Argos",
  description:
    "Respostas prontas com os dados oficiais do site: quem te representa, gastos, presença e projetos de deputados federais e senadores. Sem opinião e sem nota.",
  // Ferramenta interativa: cada ?q= daria uma página igual aos olhos de uma busca.
  robots: { index: false, follow: true },
};

function primeiro(valor: string | string[] | undefined) {
  return (Array.isArray(valor) ? valor[0] : valor)?.slice(0, 200);
}

export default function PerguntePage({ searchParams }: PageProps<"/pergunte">) {
  return (
    <article className="pagina-secoes">
      {/* Esconde o botão fixo do Argos: aqui o chat já está na página (regra em globals.css). */}
      <div data-argos-pagina hidden />
      <header className="flex flex-col gap-2">
        <p className="sobretitulo">Assistente</p>
        <h1 className="titulo-pagina">Pergunte ao Argos</h1>
        <p className="text-muted-foreground">
          O Argos é um assistente de respostas prontas, não é uma inteligência artificial. Ele reconhece as
          palavras da sua pergunta, busca nos dados oficiais do site e responde com a fonte e a data. Não dá
          opinião nem nota. Os números são os de deputados federais e senadores; para os outros cargos, ele
          mostra o link do perfil.
        </p>
        <p className="text-sm text-muted-foreground">
          O nome vem de Argos Panoptes, o gigante de cem olhos da mitologia grega, que deu origem à palavra
          panóptico. Para ver tudo sem conversar, use a{" "}
          <Link href="/parlamentares" className="underline underline-offset-2">
            busca por nome
          </Link>{" "}
          ou o{" "}
          <Link href="/#cep" className="underline underline-offset-2">
            CEP
          </Link>
          .
        </p>
      </header>

      <Suspense fallback={<p role="status" className="text-muted-foreground">Carregando o chat…</p>}>
        {searchParams.then((sp) => (
          <ArgosChat inicial={primeiro(sp.q)} />
        ))}
      </Suspense>
    </article>
  );
}
