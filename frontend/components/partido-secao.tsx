import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { GrupoFefc, PartidoDetalhe } from "@/lib/api";
import { MESES, formatarReais } from "@/lib/formato";

const CATEGORIAS_VISIVEIS = 10;

function Barras({ itens, formatar = formatarReais }: { itens: { nome: string; valor: number }[]; formatar?: (v: number) => string }) {
  const maior = Math.max(...itens.map((i) => i.valor), 0);
  return (
    <ul className="flex flex-col gap-2.5">
      {itens.map((i) => (
        <li key={i.nome} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0">{i.nome}</span>
            <span className="shrink-0 tabular-nums">{formatar(i.valor)}</span>
          </div>
          <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
            <div
              className="h-1.5 rounded-full bg-chart-1"
              style={{ width: `${maior ? Math.max(1, (i.valor / maior) * 100) : 0}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function Grupos({ titulo, grupos }: { titulo: string; grupos: GrupoFefc[] }) {
  if (grupos.length === 0) return null;
  const total = grupos.reduce((s, g) => s + g.valor, 0);
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-medium">{titulo}</h4>
      <ul className="flex flex-col gap-2">
        {grupos.map((g) => (
          <li key={g.nome} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="min-w-0">
                {g.nome}
                <span className="ml-1 text-xs text-muted-foreground">
                  {g.candidatos.toLocaleString("pt-BR")} candidaturas
                </span>
              </span>
              <span className="shrink-0 tabular-nums">
                {formatarReais(g.valor, true)}
                <span className="ml-1 text-xs text-muted-foreground">
                  {total ? ((g.valor / total) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : "0"}%
                </span>
              </span>
            </div>
            <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
              <div className="h-1.5 rounded-full bg-chart-2" style={{ width: `${total ? Math.max(1, (g.valor / total) * 100) : 0}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Finanças de um partido numa prestação de contas anual (TSE). */
export function PartidoSecao({ dados }: { dados: PartidoDetalhe }) {
  const t = dados.transferencias;
  const maiorMes = Math.max(...dados.cotas_mensais.map((m) => m.fundo_partidario + m.fefc), 0);
  const visiveis = dados.despesas_por_categoria.slice(0, CATEGORIAS_VISIVEIS);
  const demais = dados.despesas_por_categoria.slice(CATEGORIAS_VISIVEIS);
  const link = (a: number) => `/partidos/${encodeURIComponent(dados.sigla)}?ano=${a}`;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <Link href={`/partidos?ano=${dados.ano}`} className="text-sm underline underline-offset-4">
          ← Todos os partidos
        </Link>
        <h1 className="text-3xl tracking-tight">Dinheiro do {dados.sigla}</h1>
        <p className="text-muted-foreground">
          O que o partido declarou ao Tribunal Superior Eleitoral (TSE) na prestação de contas de{" "}
          {dados.ano}, somando o diretório nacional, os estaduais e os municipais.
        </p>
        {dados.anos_disponiveis.length > 1 && (
          <nav aria-label="Ano da prestação de contas" className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted-foreground">Contas de</span>
            {dados.anos_disponiveis.map((a) => (
              <Link
                key={a}
                href={link(a)}
                aria-current={a === dados.ano ? "page" : undefined}
                className={a === dados.ano ? "font-semibold underline underline-offset-4" : "underline-offset-4 hover:underline"}
              >
                {a}
              </Link>
            ))}
          </nav>
        )}
      </header>

      <section aria-labelledby="partido-resumo" className="revelar flex flex-col gap-3">
        <h2 id="partido-resumo" className="sr-only">
          Resumo
        </h2>
        <dl className="grid grid-cols-2 gap-3">
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Fundo Partidário recebido</dt>
            <dd className="numero text-2xl">{formatarReais(dados.cota_fundo_partidario, true)}</dd>
          </div>
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Fundo eleitoral (FEFC) recebido</dt>
            <dd className="numero text-2xl">{formatarReais(dados.cota_fefc, true)}</dd>
          </div>
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Receita total declarada</dt>
            <dd className="numero text-2xl">{formatarReais(dados.receita_total, true)}</dd>
          </div>
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Gasto do partido</dt>
            <dd className="numero text-2xl">{formatarReais(dados.gasto, true)}</dd>
          </div>
        </dl>
        <p className="text-xs text-muted-foreground">
          As cotas são o que o diretório nacional recebeu do TSE. O gasto não inclui repasses entre
          diretórios nem a candidaturas (veja abaixo), para o mesmo dinheiro não ser contado duas
          vezes.
        </p>
      </section>

      {dados.cotas_mensais.length > 0 && (
        <section aria-labelledby="partido-cotas" className="revelar flex flex-col gap-3">
          <div>
            <h2 id="partido-cotas" className="text-2xl">
              Cotas recebidas mês a mês
            </h2>
            <p className="text-xs text-muted-foreground">
              Fundo Partidário e Fundo Especial de Financiamento de Campanha (FEFC), pagos pelo TSE
              ao diretório nacional
            </p>
          </div>
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Cotas recebidas por mês em {dados.ano}</caption>
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="py-1.5 pr-2 font-medium">Mês</th>
                <th scope="col" className="py-1.5 pr-2 text-right font-medium">Fundo Partidário</th>
                <th scope="col" className="py-1.5 text-right font-medium">FEFC</th>
              </tr>
            </thead>
            <tbody>
              {dados.cotas_mensais.map((m) => {
                const n = Number(m.mes.slice(5, 7)) - 1;
                const larg = (v: number) => `${maiorMes ? (v / maiorMes) * 100 : 0}%`;
                return (
                  <tr key={m.mes} className="border-b border-border/70 align-top">
                    <th scope="row" className="py-1.5 pr-2 text-left font-normal">
                      {MESES[n]}
                    </th>
                    <td className="py-1.5 pr-2 text-right tabular-nums">
                      {formatarReais(m.fundo_partidario, true)}
                      <div aria-hidden className="mt-1 h-1.5 rounded-full bg-chart-1" style={{ width: larg(m.fundo_partidario) }} />
                    </td>
                    <td className="py-1.5 text-right tabular-nums">
                      {m.fefc ? formatarReais(m.fefc, true) : "—"}
                      <div aria-hidden className="mt-1 h-1.5 rounded-full bg-chart-2" style={{ width: larg(m.fefc) }} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      <section aria-labelledby="partido-receitas" className="revelar flex flex-col gap-3">
        <div>
          <h2 id="partido-receitas" className="text-2xl">
            De onde veio o dinheiro
          </h2>
          <p className="text-xs text-muted-foreground">
            Por fonte do recurso, em todos os diretórios. Não inclui o que veio de outros diretórios
            do próprio partido.
          </p>
        </div>
        <Barras itens={dados.receitas_por_fonte} formatar={(v) => formatarReais(v, true)} />
      </section>

      <section aria-labelledby="partido-despesas" className="revelar flex flex-col gap-3">
        <div>
          <h2 id="partido-despesas" className="text-2xl">
            Em que o partido gastou
          </h2>
          <p className="text-xs text-muted-foreground">
            Por tipo de despesa, como o partido classificou. Só gastos: sem transferências.
          </p>
        </div>
        <Barras itens={visiveis} formatar={(v) => formatarReais(v, true)} />
        {demais.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer underline underline-offset-4">
              Ver mais {demais.length} tipos de despesa
            </summary>
            <div className="mt-3">
              <Barras itens={demais} formatar={(v) => formatarReais(v, true)} />
            </div>
          </details>
        )}
      </section>

      <section aria-labelledby="partido-transf" className="revelar flex flex-col gap-3">
        <div>
          <h2 id="partido-transf" className="text-2xl">
            Dinheiro que só mudou de mãos
          </h2>
          <p className="text-xs text-muted-foreground">
            Está fora do gasto acima: o dinheiro que sai de um diretório entra em outro, ou chega a
            uma candidatura, e já aparece lá como receita.
          </p>
        </div>
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Repassado a candidaturas</dt>
            <dd className="numero text-2xl">{formatarReais(t.repassadas_a_candidatos, true)}</dd>
          </div>
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Enviado a outros diretórios do partido</dt>
            <dd className="numero text-2xl">{formatarReais(t.enviadas_a_outros_diretorios, true)}</dd>
          </div>
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Recebido de outros diretórios</dt>
            <dd className="numero text-2xl">{formatarReais(t.recebidas_de_outros_diretorios, true)}</dd>
          </div>
          {t.outras_enviadas > 0 && (
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Outras transferências enviadas</dt>
              <dd className="numero text-2xl">{formatarReais(t.outras_enviadas, true)}</dd>
            </div>
          )}
        </dl>
      </section>

      {dados.fefc_fp && (
        <section aria-labelledby="partido-fefc" className="revelar flex flex-col gap-4">
          <div>
            <h2 id="partido-fefc" className="text-2xl">
              Fundos nas candidaturas de {dados.fefc_fp.ano}
            </h2>
            <p className="text-xs text-muted-foreground">
              Quanto das campanhas chegou a cada grupo, por gênero e por cor ou raça (autodeclarados
              pelas candidaturas)
            </p>
          </div>
          {dados.fefc_fp.fefc_total_partido != null && (
            <p className="text-sm">
              Total do fundo eleitoral do partido na eleição:{" "}
              <span className="numero text-lg">{formatarReais(dados.fefc_fp.fefc_total_partido, true)}</span>
            </p>
          )}
          <Grupos titulo="Fundo eleitoral (FEFC) por gênero" grupos={dados.fefc_fp.fefc_por_genero} />
          <Grupos titulo="Fundo eleitoral (FEFC) por cor ou raça" grupos={dados.fefc_fp.fefc_por_cor_raca} />
          <Grupos titulo="Fundo Partidário por gênero" grupos={dados.fefc_fp.fp_por_genero} />
          <Grupos titulo="Fundo Partidário por cor ou raça" grupos={dados.fefc_fp.fp_por_cor_raca} />
          <FonteRodape fonte={dados.fefc_fp.fonte_nome} url={dados.fefc_fp.fonte_url} atualizadoEm={dados.fefc_fp.atualizado_em} />
        </section>
      )}

      <div className="nota text-sm text-muted-foreground">
        São valores declarados pelo partido na prestação de contas, que a Justiça Eleitoral
        analisa depois; o Panóptico mostra o que foi declarado, sem juízo sobre as contas.
      </div>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
