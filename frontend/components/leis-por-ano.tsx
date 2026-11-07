/**
 * Filtro "Virou lei" de /projetos (versão B aprovada): um cartão por ano com a contagem e uma
 * barra de quantidade, todos fechados de início. Sem JavaScript: abrir um ano que ainda não foi
 * carregado leva ao endereço com `ano_lei`, que volta com aquele ano aberto e a lista dele (20 por
 * página). A ordem é só a cronológica; a barra mede quantidade, não é ranking.
 */
import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { LinkExterno } from "@/components/link-externo";
import type { BlocoLeis, FiltrosProjetos, NormaItem } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { comArtigo, composicaoDoAno, contagemLeis, larguraBarra, origensDaLei } from "@/lib/normas";
import { enderecoProjetos } from "@/lib/projetos";

export function NormaCartao({ n }: { n: NormaItem }) {
  const origens = origensDaLei(n.projetos);
  return (
    <div className="flex flex-col gap-1 py-3">
      <p className="text-sm text-muted-foreground tabular-nums">
        {formatarData(n.data)}
        {origens.length > 0 && (
          <>
            {" · veio "}
            {origens.map((o, i) => (
              <span key={o.identificacao}>
                {i > 0 && " e "}
                {o.link ? (
                  <Link href={o.link} className="underline underline-offset-4">
                    {comArtigo(o.identificacao)}
                  </Link>
                ) : (
                  comArtigo(o.identificacao)
                )}
              </span>
            ))}
          </>
        )}
      </p>
      <p className="font-semibold">{n.nome}</p>
      <p className="line-clamp-4 text-sm leading-relaxed">{n.ementa}</p>
      <p className="text-sm text-muted-foreground">Texto oficial: {n.nome_oficial}</p>
      <LinkExterno href={n.url} className="alvo-link self-start text-sm font-medium underline underline-offset-4">
        Ler o texto da lei
      </LinkExterno>
    </div>
  );
}

export function LeisPorAno({ leis, filtros }: { leis: BlocoLeis; filtros: FiltrosProjetos }) {
  const maior = Math.max(0, ...leis.anos.map((a) => a.total));
  const paginas = Math.max(1, Math.ceil(leis.total_ano / leis.por_pagina));
  return (
    <section aria-labelledby="leis-titulo" className="flex flex-col gap-3">
      <div className="nota flex flex-col gap-1 text-sm">
        <h2 id="leis-titulo" className="font-semibold">
          {contagemLeis(leis.total)}
          {leis.desde ? ` desde ${leis.desde}` : ""}
          {filtros.q && <> para &quot;{filtros.q}&quot;</>}
        </h2>
        <p className="text-muted-foreground">
          Leis ordinárias, leis complementares e emendas à Constituição federais, agrupadas pelo ano da lei. A barra mostra a
          quantidade; o número está escrito ao lado. Toque num ano para ver as leis dele.
        </p>
        <p className="text-muted-foreground">
          Ficam de fora decretos legislativos e resoluções. Assembleias e câmaras municipais ainda não dizem quando um projeto
          vira lei. Neste modo, só a busca (por palavra ou pelo número da lei) filtra a lista.
        </p>
      </div>

      {leis.anos.length === 0 ? (
        <p className="text-muted-foreground">Nenhuma lei encontrada{filtros.q ? ` para "${filtros.q}"` : ""}.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {leis.anos.map((a) => {
            const aberto = leis.ano === a.ano;
            return (
              <li key={a.ano} id={`ano-${a.ano}`} className="scroll-mt-20">
                <details open={aberto} className="border border-border bg-card">
                  <summary className="flex min-h-11 cursor-pointer flex-col gap-1.5 px-[var(--esp-4)] py-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="numero text-2xl">{a.ano}</span>
                      <span className="text-sm font-medium tabular-nums">{contagemLeis(a.total)}</span>
                    </span>
                    <span aria-hidden className="block h-1.5 w-full bg-muted">
                      <span className="block h-full bg-bronze" style={{ width: `${larguraBarra(a.total, maior)}%` }} />
                    </span>
                  </summary>
                  <div className="flex flex-col gap-2 border-t border-border px-[var(--esp-4)] pb-3">
                    <p className="pt-3 text-sm text-muted-foreground">{composicaoDoAno(a)}.</p>
                    {aberto ? (
                      <>
                        <ul className="lista-fios">
                          {leis.itens.map((n) => (
                            <li key={`${n.tipo}-${n.numero}-${n.ano}`}>
                              <NormaCartao n={n} />
                            </li>
                          ))}
                        </ul>
                        {paginas > 1 && (
                          <nav aria-label={`Páginas das leis de ${a.ano}`} className="flex items-center justify-between gap-2 text-sm">
                            {leis.pagina > 1 ? (
                              <Link
                                href={`${enderecoProjetos(filtros, { ano_lei: String(a.ano), pagina: String(leis.pagina - 1) })}#ano-${a.ano}`}
                                className="alvo-link px-1 font-medium underline underline-offset-4"
                              >
                                ← Anteriores
                              </Link>
                            ) : (
                              <span />
                            )}
                            <span className="text-muted-foreground tabular-nums">
                              Página {leis.pagina} de {paginas}
                            </span>
                            {leis.pagina < paginas ? (
                              <Link
                                href={`${enderecoProjetos(filtros, { ano_lei: String(a.ano), pagina: String(leis.pagina + 1) })}#ano-${a.ano}`}
                                className="alvo-link px-1 font-medium underline underline-offset-4"
                              >
                                Próximas →
                              </Link>
                            ) : (
                              <span />
                            )}
                          </nav>
                        )}
                      </>
                    ) : (
                      <Link
                        href={`${enderecoProjetos(filtros, { ano_lei: String(a.ano) })}#ano-${a.ano}`}
                        className="botao-linha self-start px-[var(--esp-4)]"
                      >
                        Ver as leis de {a.ano}
                      </Link>
                    )}
                  </div>
                </details>
              </li>
            );
          })}
        </ul>
      )}
      <FonteRodape fonte={leis.fonte_nome} url={leis.fonte_url} atualizadoEm={leis.atualizado_em} />
    </section>
  );
}
