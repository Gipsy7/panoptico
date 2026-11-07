import { TermoOficial } from "@/components/termo-oficial";

/** "Como separamos": a regra do recorte, com os termos oficiais. */
export function ComoSeparamos() {
  return (
    <details className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
      <summary className="min-h-6 cursor-pointer font-medium">Como separamos</summary>
      <div className="mt-2 flex flex-col gap-2">
        <p>
          Pelo texto oficial de cada votação. <strong>Sobre o texto</strong>{" "}
          <span className="text-xs text-muted-foreground">(votação de mérito)</span>: aprova ou rejeita o projeto, uma
          emenda, um <TermoOficial id="destaque">destaque</TermoOficial> ou a redação final; também a escolha de
          autoridades no Senado.
        </p>
        <p>
          <strong>Procedimento</strong>: decide como e quando votar, como o pedido de{" "}
          <TermoOficial id="urgencia">urgência</TermoOficial>, de adiamento, de retirada de pauta ou de votação por
          artigos. O que não dá para classificar fica em procedimento.
        </p>
      </div>
    </details>
  );
}
