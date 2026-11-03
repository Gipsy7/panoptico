"use client";

import { FonteRodape } from "@/components/fonte-rodape";
import { agrupar, totalDe, type ItemBancada } from "@/lib/cadeiras";

/**
 * Bancada de uma casa: contagem literal por partido ("PNA 11 · MRB 8 ...") e uma barra
 * horizontal neutra, uma fatia por partido na proporção das cadeiras. Partido só em texto,
 * sem cor por partido. Com `onEscolher`, cada partido vira botão.
 */
export function Bancada({
  itens,
  total,
  fonte,
  atualizadoEm,
  fonteUrl,
  onEscolher,
  escolhido,
  titulo,
}: {
  itens: ItemBancada[];
  total?: number;
  fonte: string;
  atualizadoEm?: string | null;
  fonteUrl?: string;
  onEscolher?: (partido: string) => void;
  escolhido?: string | null;
  titulo?: string;
}) {
  const lista = agrupar(itens);
  const soma = total ?? totalDe(lista);
  if (soma === 0) {
    return (
      <div className="flex flex-col gap-2">
        {titulo && <h3 className="text-lg font-semibold">{titulo}</h3>}
        <p className="text-sm text-muted-foreground">Sem dados desta bancada na fonte.</p>
        <FonteRodape fonte={fonte} url={fonteUrl} atualizadoEm={atualizadoEm} />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {titulo && (
        <h3 className="text-lg font-semibold">
          {titulo} <span className="text-sm font-normal text-muted-foreground tabular-nums">· {soma} no total</span>
        </h3>
      )}
      <div
        role="img"
        aria-label={`Barra das bancadas: ${lista.map((i) => `${i.partido} ${i.n}`).join(", ")}. Total ${soma}.`}
        className="flex h-2.5 w-full gap-px overflow-hidden rounded-[2px] bg-muted"
      >
        {lista.map((i, k) => (
          <span
            key={i.partido}
            className={`h-full ${escolhido === i.partido ? "bg-bronze" : k % 2 === 0 ? "bg-chart-3" : "bg-chart-4"}`}
            style={{ flexGrow: i.n, flexBasis: 0 }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-sm tabular-nums">
        {lista.map((i) => (
          <li key={i.partido}>
            {onEscolher ? (
              <button
                type="button"
                aria-pressed={escolhido === i.partido}
                onClick={() => onEscolher(i.partido)}
                className="min-h-11 rounded-md px-1.5 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze aria-pressed:bg-accent aria-pressed:font-semibold"
              >
                {i.partido} <span className="font-semibold">{i.n}</span>
              </button>
            ) : (
              <span>
                {i.partido} <span className="font-semibold">{i.n}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
      <FonteRodape fonte={fonte} url={fonteUrl} atualizadoEm={atualizadoEm} />
    </div>
  );
}
