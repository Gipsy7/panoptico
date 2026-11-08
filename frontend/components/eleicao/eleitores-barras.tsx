import { FonteRodape } from "@/components/fonte-rodape";
import type { Eleitores } from "@/lib/api";
import { formatarPct, formatarVotos } from "@/lib/eleicao";

/** Moradores, eleitores e quem votou, em três barras na mesma escala (versão C, Frente 5). */
export function EleitoresBarras({ d }: { d: Eleitores }) {
  const moradores = d.populacao?.valor ?? null;
  const maximo = Math.max(moradores ?? 0, d.eleitores);
  const linhas = [
    moradores !== null
      ? {
          rotulo: `Moradores (${d.populacao!.ano})`,
          valor: moradores,
          nota: null as string | null,
        }
      : null,
    {
      rotulo: `Podiam votar em ${d.ano}`,
      valor: d.eleitores,
      nota:
        d.eleitores_por_100_moradores !== null
          ? `${d.eleitores_por_100_moradores} para cada 100 moradores`
          : null,
    },
    {
      rotulo: `Votaram em ${d.ano}`,
      valor: d.votaram,
      nota: `${formatarPct(d.pct_votaram, 1)} de quem podia votar`,
    },
  ].filter(
    (l): l is { rotulo: string; valor: number; nota: string | null } =>
      l !== null,
  );

  return (
    <section aria-labelledby="eleitores-titulo" className="flex flex-col gap-3">
      <h2 id="eleitores-titulo" className="text-xl">
        Moradores e eleitores
      </h2>
      <ul className="flex flex-col gap-2 text-sm">
        {linhas.map((l) => (
          <li key={l.rotulo} className="flex flex-col gap-0.5">
            <p className="flex items-baseline justify-between gap-2">
              <span className="text-muted-foreground">{l.rotulo}</span>
              <span className="tabular-nums">{formatarVotos(l.valor)}</span>
            </p>
            <span
              aria-hidden
              className="block h-2 w-full overflow-hidden rounded-[2px] bg-muted"
            >
              <span
                className="block h-full rounded-[2px] bg-bronze"
                style={{ width: `${maximo ? (100 * l.valor) / maximo : 0}%` }}
              />
            </span>
            {l.nota && (
              <span className="text-xs text-muted-foreground">{l.nota}</span>
            )}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Eleitores aptos na eleição de {d.ano} (soma das zonas da cidade); quem
        votou fora, em trânsito, conta onde votou.
      </p>
      <FonteRodape
        fonte={
          d.populacao
            ? `${d.fonte_nome}; ${d.populacao.fonte_nome}`
            : d.fonte_nome
        }
        url={d.fonte_url}
        atualizadoEm={d.atualizado_em}
        semAviso
      />
    </section>
  );
}
