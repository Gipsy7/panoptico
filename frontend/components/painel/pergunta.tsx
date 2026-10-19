/**
 * Pergunta expansível de "Para entender os números": a pergunta e a resposta curta ficam
 * à vista; a explicação (e um visual, se houver) abre ao tocar. <details> nativo, sem JS.
 * O `id` permite linkar de dentro de uma seção (ex.: href="#entender-presenca"); o
 * <AbasDetalhe> abre o <details> quando o hash aponta para ele.
 *
 * Uso (servidor):
 *   <ListaPerguntas titulo="Para entender os números">
 *     <Pergunta id="entender-presenca" pergunta="O que entra na conta da presença?"
 *       resposta="Todas as votações do ano; só o voto registrado conta como presença">
 *       <p>Explicação curta…</p>
 *     </Pergunta>
 *   </ListaPerguntas>
 * Linguagem factual: a pergunta não pode sugerir juízo ("Ele trabalha?").
 */
import type { ReactNode } from "react";

export function ListaPerguntas({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section aria-labelledby="entender-titulo" className="flex flex-col gap-3">
      <h2 id="entender-titulo" className="text-2xl">
        {titulo}
      </h2>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}

export function Pergunta({
  id,
  pergunta,
  resposta,
  children,
}: {
  id: string;
  pergunta: string;
  resposta: string;
  children: ReactNode;
}) {
  return (
    <details id={id} className="group rounded-[var(--radius)] border border-border bg-card">
      <summary className="grid min-h-11 cursor-pointer list-none grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze [&::-webkit-details-marker]:hidden">
        <span className="font-medium">{pergunta}</span>
        <span
          aria-hidden
          className="row-span-2 self-center text-lg text-muted-foreground transition-transform duration-200 group-open:rotate-90 motion-reduce:transition-none"
        >
          ›
        </span>
        <span className="numero text-lg leading-snug">{resposta}</span>
      </summary>
      <div className="flex flex-col gap-3 px-4 pb-4 text-sm leading-relaxed">{children}</div>
    </details>
  );
}
