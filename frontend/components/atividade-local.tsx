import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { VereadorDetalhe, VotacoesLocais } from "@/lib/api";
import { MESES, formatarData, formatarReais } from "@/lib/formato";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

/** Presença nas sessões plenárias, com a média da casa ao lado. */
export function PresencaLocalSecao({ v, nomeCasa }: { v: VereadorDetalhe; nomeCasa: string }) {
  const p = v.presenca;
  return (
    <section aria-labelledby="presenca-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="presenca-titulo" className="text-2xl">
          Presença nas sessões
        </h2>
        <p className="text-xs text-muted-foreground">Ano atual e anterior, durante o mandato</p>
      </div>
      {!p ? (
        <p className="text-sm text-muted-foreground">
          A {nomeCasa} não publica a lista de presença nas sessões em dados abertos.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3">
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Esteve em</dt>
              <dd className="numero text-3xl">
                {p.presencas} de {p.sessoes}
              </dd>
              <dd className="text-xs text-muted-foreground">sessões</dd>
            </div>
            {p.media_casa !== null && (
              <div className="figura">
                <dt className="text-sm text-muted-foreground">Média da {nomeCasa}</dt>
                <dd className="numero text-3xl">{PCT.format(p.media_casa)}%</dd>
                <dd className="text-xs text-muted-foreground">das sessões, entre quem está no cargo</dd>
              </div>
            )}
          </dl>
          <p className="text-xs text-muted-foreground">
            Contam as sessões plenárias com a lista de presença lançada no sistema. Ausências
            justificadas (licença, missão oficial) não aparecem separadas.
          </p>
        </>
      )}
    </section>
  );
}

/** Como votou nas votações nominais da casa. */
export function VotacoesLocaisSecao({
  dados,
  nomeCasa,
  caminho,
}: {
  dados: VotacoesLocais;
  nomeCasa: string;
  /** Endereço do perfil, para a paginação. */
  caminho: string;
}) {
  const paginas = Math.max(1, Math.ceil(dados.total / dados.por_pagina));
  return (
    <section aria-labelledby="votacoes-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="votacoes-titulo" className="text-2xl">
          Como votou
        </h2>
        <p className="text-xs text-muted-foreground">
          Votações nominais da {nomeCasa}, ano atual e anterior
        </p>
      </div>
      {!dados.casa_registra ? (
        <p className="text-sm text-muted-foreground">
          A {nomeCasa} não publica o voto de cada parlamentar em dados abertos. Por isso,
          aqui não aparece como cada um votou.
        </p>
      ) : dados.total === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum voto nominal registrado neste período.</p>
      ) : (
        <>
          <p className="text-sm">
            Registrou voto em <span className="numero">{dados.votou}</span> das{" "}
            <span className="numero">{dados.total}</span> votações nominais em que aparece na lista.
          </p>
          <ul className="lista-fios flex flex-col">
            {dados.itens.map((v, i) => (
              <li key={i} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                <span className="min-w-0">
                  {v.url ? (
                    <a href={v.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                      {v.materia}
                    </a>
                  ) : (
                    v.materia
                  )}
                  <span className="block text-xs text-muted-foreground">
                    {[v.data && formatarData(v.data), v.resultado, `${v.sim} sim, ${v.nao} não`].filter(Boolean).join(" · ")}
                  </span>
                </span>
                <span className="pilula shrink-0">{v.voto}</span>
              </li>
            ))}
          </ul>
          {paginas > 1 && (
            <nav aria-label="Páginas das votações" className="flex items-center gap-4 text-sm">
              {dados.pagina > 1 && (
                <Link href={`${caminho}?votos=${dados.pagina - 1}#votacoes-titulo`} className="underline underline-offset-2">
                  Mais recentes
                </Link>
              )}
              <span className="text-muted-foreground">
                Página {dados.pagina} de {paginas}
              </span>
              {dados.pagina < paginas && (
                <Link href={`${caminho}?votos=${dados.pagina + 1}#votacoes-titulo`} className="underline underline-offset-2">
                  Mais antigas
                </Link>
              )}
            </nav>
          )}
          <p className="text-xs text-muted-foreground">
            Votações simbólicas, em que não se anota o voto de cada um, não aparecem.
          </p>
        </>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

/** Gastos do gabinete reembolsados (verba indenizatória), com a média da casa. */
export function GastosLocaisSecao({ v, nomeCasa }: { v: VereadorDetalhe; nomeCasa: string }) {
  const g = v.gastos;
  if (!g) return null;
  const maior = g.por_categoria[0]?.valor ?? 0;
  return (
    <section aria-labelledby="gastos-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="gastos-titulo" className="text-2xl">
          Gastos do gabinete
        </h2>
        <p className="text-xs text-muted-foreground">Verba indenizatória (reembolsos ao gabinete)</p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        <div className="figura">
          <dt className="text-sm text-muted-foreground">
            Total em {g.ano}
            {g.ate_mes ? ` (até ${MESES[g.ate_mes - 1]})` : ""}
          </dt>
          <dd className="numero text-3xl">{formatarReais(g.total, true)}</dd>
        </div>
        {g.media_casa !== null && (
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Média por parlamentar da {nomeCasa}</dt>
            <dd className="numero text-3xl">{formatarReais(g.media_casa, true)}</dd>
          </div>
        )}
      </dl>
      <ul className="flex flex-col gap-2.5">
        {g.por_categoria.map((c) => (
          <li key={c.categoria} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="min-w-0">{c.categoria}</span>
              <span className="shrink-0 tabular-nums">{formatarReais(c.valor, true)}</span>
            </div>
            <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
              <div
                className="h-1.5 rounded-full bg-chart-1"
                style={{ width: `${maior > 0 ? Math.max(1, (100 * c.valor) / maior) : 0}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Valores reembolsados como a {nomeCasa} publica, por mês de fechamento. A média inclui quem
        está no cargo hoje; quem não pediu reembolso entra com zero.
      </p>
    </section>
  );
}
