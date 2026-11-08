import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { CadeirasPartido, CadeirasPorPartido, PartidoNaLista } from "@/lib/api";
import { formatarReaisCompacto } from "@/lib/formato";

/**
 * Topo de Partidos (redesenho, protótipo 3): lista reta com a barra das cadeiras na Câmara num tom só
 * (a cor não diz nada sobre o partido) e a ficha do partido escolhido ao lado (abaixo, no celular):
 * Câmara, Senado, prefeitos e vereadores eleitos e o Fundo Partidário declarado ao TSE.
 */
const num = (n: number) => n.toLocaleString("pt-BR");

export function PartidosCadeiras({
  dados,
  contas,
  anoContas,
  escolhido,
  hrefPartido,
}: {
  dados: CadeirasPorPartido;
  contas: PartidoNaLista[];
  anoContas: number | null;
  escolhido?: string;
  hrefPartido: (sigla: string) => string;
}) {
  const noCongresso = dados.itens.filter((i) => i.camara > 0 || i.senado > 0);
  const outros = dados.itens.filter((i) => i.camara === 0 && i.senado === 0);
  const atual =
    dados.itens.find((i) => i.partido.toLowerCase() === escolhido?.toLowerCase()) ?? noCongresso[0] ?? dados.itens[0];
  const maior = Math.max(1, ...noCongresso.map((i) => i.camara));
  if (!atual) return null;
  return (
    <section aria-labelledby="cadeiras-titulo" className="flex flex-col gap-4">
      <h2 id="cadeiras-titulo" className="text-xl">
        Cadeiras de cada partido
      </h2>
      <div className="grid items-start gap-6 lg:grid-cols-2 lg:gap-9">
        <div className="flex flex-col">
          <p className="mb-2 text-sm text-muted-foreground">
            Deputados federais no cargo hoje, de {num(dados.total_camara)}. Toque num partido para ver a ficha.
          </p>
          <ul className="border-t border-foreground">
            {noCongresso.map((i) => {
              const sel = i.partido === atual.partido;
              return (
                <li key={i.partido}>
                  <Link
                    href={hrefPartido(i.partido)}
                    scroll={false}
                    aria-current={sel ? "true" : undefined}
                    className="grid min-h-12 grid-cols-[8.25rem_1fr_2.5rem] items-center gap-2.5 border-b border-l-4 border-b-border px-2 sm:grid-cols-[9rem_1fr_2.75rem]"
                    style={{
                      borderLeftColor: sel ? "var(--tema-votos)" : "transparent",
                      background: sel ? "var(--card)" : undefined,
                    }}
                  >
                    <span className="truncate text-sm font-semibold">{i.partido}</span>
                    <span className="h-2.5 bg-muted" aria-hidden>
                      <span
                        className="block h-full"
                        style={{ width: `${(100 * i.camara) / maior}%`, background: "var(--tema-votos)" }}
                      />
                    </span>
                    <span className="numero text-right">
                      {num(i.camara)}
                      <span className="sr-only"> deputados</span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">Um tom só: a cor não diz nada sobre o partido.</p>
          {outros.length > 0 && (
            <p className="mt-3 text-sm">
              <span className="text-muted-foreground">Sem cadeira no Congresso, com prefeitos ou vereadores: </span>
              {outros.map((i, k) => (
                <span key={i.partido}>
                  {k > 0 && ", "}
                  <Link
                    href={hrefPartido(i.partido)}
                    scroll={false}
                    aria-current={i.partido === atual.partido ? "true" : undefined}
                    className="underline underline-offset-4"
                  >
                    {i.partido}
                  </Link>
                </span>
              ))}
            </p>
          )}
        </div>
        <Ficha p={atual} dados={dados} contas={contas} anoContas={anoContas} />
      </div>
    </section>
  );
}

function Ficha({
  p,
  dados,
  contas,
  anoContas,
}: {
  p: CadeirasPartido;
  dados: CadeirasPorPartido;
  contas: PartidoNaLista[];
  anoContas: number | null;
}) {
  const conta = p.sigla_contas ? contas.find((c) => c.sigla === p.sigla_contas) : undefined;
  const item = (rotulo: string, valor: string, apoio: string) => (
    <div className="border-t-2 border-foreground pt-2">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="numero text-2xl">{valor}</dd>
      <dd className="text-sm text-muted-foreground">{apoio}</dd>
    </div>
  );
  return (
    <div
      id="ficha"
      className="flex scroll-mt-24 flex-col gap-4 border border-t-4 border-border bg-card p-4 lg:sticky lg:top-24"
      style={{ borderTopColor: "var(--tema-votos)" }}
      aria-live="polite"
    >
      <p className="text-xs font-semibold tracking-wider uppercase" style={{ color: "var(--tema-votos)" }}>
        Ficha do partido
      </p>
      <h3 className="-mt-2 text-2xl">{p.partido}</h3>
      <dl className="grid grid-cols-2 gap-4">
        {item("Na Câmara", num(p.camara), `de ${num(dados.total_camara)} deputados`)}
        {item("No Senado", num(p.senado), `de ${num(dados.total_senado)} senadores`)}
        {dados.ano_municipal != null && item("Prefeitos", num(p.prefeitos), `eleitos em ${dados.ano_municipal}`)}
        {dados.ano_municipal != null && item("Vereadores", num(p.vereadores), `eleitos em ${dados.ano_municipal}`)}
        {conta &&
          anoContas != null &&
          item("Fundo Partidário", formatarReaisCompacto(conta.cota_fundo_partidario), `recebido em ${anoContas}`)}
      </dl>
      <ul className="flex flex-col gap-1 text-sm">
        {p.sigla_contas && (
          <li>
            <Link href={`/partidos/${encodeURIComponent(p.sigla_contas)}`} className="underline underline-offset-4">
              Dinheiro do {p.partido}: de onde veio e para onde foi
            </Link>
          </li>
        )}
        {(p.camara > 0 || p.senado > 0) && (
          <li>
            <Link href={`/parlamentares?partido=${encodeURIComponent(p.partido)}`} className="underline underline-offset-4">
              Os deputados e senadores do {p.partido}
            </Link>
          </li>
        )}
      </ul>
      <p className="text-xs text-muted-foreground">
        Prefeitos e vereadores pelo partido com que foram eleitos; quem trocou de partido depois segue contado no da
        eleição.
      </p>
      {dados.fontes.map((f) => (
        <FonteRodape key={f.nome} fonte={f.nome} url={f.url} atualizadoEm={f.atualizado_em} />
      ))}
    </div>
  );
}
