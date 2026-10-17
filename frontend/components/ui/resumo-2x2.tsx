/**
 * Cartão-resumo: quatro contadores em grade 2x2 que dão a dimensão da lista antes dela.
 * Número em serifa (tabular), rótulo embaixo e, opcionalmente, uma linha de apoio (ex.: média).
 */
export type ItemResumo = { rotulo: string; valor: string; apoio?: string };

export function Resumo2x2({ titulo, itens }: { titulo: string; itens: ItemResumo[] }) {
  return (
    <section aria-label={titulo} className="grid grid-cols-2 border border-border bg-card">
      {itens.map((item, i) => (
        <div
          key={item.rotulo}
          className={`flex min-w-0 flex-col gap-[var(--esp-1)] p-[var(--esp-4)] ${
            i % 2 === 1 ? "border-l border-border" : ""
          } ${i >= 2 ? "border-t border-border" : ""}`}
        >
          <p className="numero text-[1.625rem] leading-none break-words sm:text-[2.5rem]">{item.valor}</p>
          <p className="text-sm">{item.rotulo}</p>
          {item.apoio && <p className="text-sm text-muted-foreground">{item.apoio}</p>}
        </div>
      ))}
    </section>
  );
}
