import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { Casa, Gastos } from "@/lib/api";
import { CASA_CURTA, MESES, formatarData, formatarReais } from "@/lib/formato";

export function GastosSecao({
  gastos,
  casa,
  parlamentarId,
}: {
  gastos: Gastos;
  casa: Casa;
  parlamentarId: number;
}) {
  const periodo =
    gastos.ultimo_mes && gastos.ultimo_mes < 12 ? ` (jan a ${MESES[gastos.ultimo_mes - 1]})` : "";
  const maiorCategoria = gastos.por_categoria[0]?.total ?? 0;

  return (
    <section aria-labelledby="gastos-titulo" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 id="gastos-titulo" className="text-xl font-semibold">
            Gastos do gabinete
          </h2>
          <p className="text-xs text-muted-foreground">{gastos.fonte_nome}</p>
        </div>
        {gastos.anos_disponiveis.length > 1 && (
          <nav aria-label="Escolher ano" className="flex gap-1">
            {gastos.anos_disponiveis.map((ano) => (
              <Link
                key={ano}
                href={`/parlamentar/${parlamentarId}?ano=${ano}`}
                scroll={false}
                aria-current={ano === gastos.ano ? "page" : undefined}
                className="rounded-lg px-3 py-1.5 text-sm ring-1 ring-foreground/10 aria-[current=page]:bg-primary aria-[current=page]:text-primary-foreground"
              >
                {ano}
              </Link>
            ))}
          </nav>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <dt className="text-sm text-muted-foreground">
            Total em {gastos.ano}
            {periodo}
          </dt>
          <dd className="text-2xl font-bold tabular-nums">{formatarReais(gastos.total, true)}</dd>
        </div>
        <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <dt className="text-sm text-muted-foreground">Média por parlamentar do {CASA_CURTA[casa]}</dt>
          <dd className="text-2xl font-bold tabular-nums">
            {formatarReais(gastos.media_casa, true)}
          </dd>
        </div>
      </dl>

      {gastos.por_categoria.length === 0 ? (
        <p className="text-muted-foreground">Nenhum gasto registrado em {gastos.ano}.</p>
      ) : (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Onde o dinheiro foi gasto</h3>
          <ul className="flex flex-col gap-3">
            {gastos.por_categoria.map((c) => {
              const largura = maiorCategoria > 0 ? Math.max(0, (c.total / maiorCategoria) * 100) : 0;
              const parte = gastos.total > 0 ? Math.round((c.total / gastos.total) * 100) : 0;
              return (
                <li
                  key={c.categoria}
                  className="group flex flex-col gap-1"
                  title={`${c.categoria}: ${formatarReais(c.total)} (${parte}% do total)`}
                >
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="line-clamp-2">{c.categoria}</span>
                    <span className="shrink-0 font-medium tabular-nums">
                      {formatarReais(c.total, true)}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted" aria-hidden>
                    <div
                      className="h-2 rounded-full bg-chart-1 transition-opacity group-hover:opacity-80"
                      style={{ width: `${largura}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {gastos.maiores_despesas.length > 0 && (
        <details className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <summary className="cursor-pointer font-medium">
            Ver os {gastos.maiores_despesas.length} maiores gastos de {gastos.ano}
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th scope="col" className="py-1 pr-3 font-normal">Data</th>
                  <th scope="col" className="py-1 pr-3 font-normal">Fornecedor</th>
                  <th scope="col" className="py-1 text-right font-normal">Valor</th>
                </tr>
              </thead>
              <tbody>
                {gastos.maiores_despesas.map((d, i) => (
                  <tr key={i} className="border-t align-top">
                    <td className="py-2 pr-3 whitespace-nowrap">
                      {d.data ? formatarData(d.data) : `${MESES[d.mes - 1]}/${gastos.ano}`}
                    </td>
                    <td className="py-2 pr-3">
                      <span className="block">{d.fornecedor ?? "Não informado"}</span>
                      <span className="block text-xs text-muted-foreground">{d.categoria}</span>
                      {d.url_documento && (
                        <a
                          href={d.url_documento}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs underline underline-offset-2"
                        >
                          Ver nota fiscal
                        </a>
                      )}
                    </td>
                    <td className="py-2 text-right whitespace-nowrap tabular-nums">
                      {formatarReais(d.valor)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <FonteRodape
        fonte={casa === "camara" ? "Câmara dos Deputados" : "Senado Federal"}
        url={gastos.fonte_url}
        atualizadoEm={gastos.atualizado_em}
      />
    </section>
  );
}
