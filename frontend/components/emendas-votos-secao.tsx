import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { EmendasDosMaisVotados } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const INTEIRO = new Intl.NumberFormat("pt-BR");

/**
 * "Os mais votados aqui e o que enviaram" (docs/DECISOES.md, 2026-11-14, protótipo 3A): os
 * deputados federais em exercício mais votados na cidade e as emendas individuais pagas a ela.
 * Dois números da mesma cidade, lado a lado; a tela não diz que um explica o outro.
 */
export function EmendasVotosSecao({ dados }: { dados: EmendasDosMaisVotados }) {
  const cidade = dados.municipio.nome;
  const periodo =
    dados.emendas_de && dados.emendas_ate
      ? dados.emendas_de === dados.emendas_ate
        ? `em ${dados.emendas_de}`
        : `de ${dados.emendas_de} a ${dados.emendas_ate}`
      : "no período carregado";
  const fora = dados.fora_por_nao_estar_em_exercicio;

  return (
    <section aria-labelledby="emendas-votos-titulo" className="revelar flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id="emendas-votos-titulo" className="text-2xl">
          Os deputados federais mais votados em {cidade} e o que enviaram
        </h2>
        <p className="text-sm text-muted-foreground">
          Votos que cada um teve na cidade em {dados.ano_eleicao} e emendas individuais pagas a {cidade} {periodo}.
        </p>
      </div>

      <ol className="lista-fios flex flex-col">
        {dados.itens.map((i) => (
          <li key={i.parlamentar_id} className="flex items-baseline justify-between gap-4 py-3">
            <span className="flex min-w-0 flex-col">
              <Link
                href={`/parlamentar/${i.parlamentar_id}`}
                className="inline-block min-h-6 font-semibold underline underline-offset-2"
              >
                {i.nome}
              </Link>
              <span className="text-sm text-muted-foreground">
                {[i.partido, i.uf].filter(Boolean).join("-")} · {INTEIRO.format(i.votos)} votos aqui · {i.posicao}º mais
                votado
              </span>
            </span>
            <span className="flex shrink-0 flex-col items-end text-right">
              <span className="font-heading text-xl tabular-nums">{formatarReais(i.emendas_pagas, true)}</span>
              <span className="text-xs text-muted-foreground">emendas pagas</span>
            </span>
          </li>
        ))}
      </ol>

      <p className="text-sm">
        Juntos, enviaram <strong>{formatarReais(dados.emendas_dos_listados, true)}</strong> dos{" "}
        <strong>{formatarReais(dados.emendas_individuais_da_cidade, true)}</strong> em emendas individuais pagas a{" "}
        {cidade} {periodo}.
      </p>

      <p className="text-sm text-muted-foreground">
        A lista traz só quem está no cargo hoje.{" "}
        {fora > 0 &&
          `${fora === 1 ? "Um candidato mais votado ficou" : `${fora} candidatos mais votados ficaram`} de fora, porque não se ${fora === 1 ? "elegeu" : "elegeram"} ou ${fora === 1 ? "saiu" : "saíram"} do cargo. `}
        Quem não enviou nada aparece com R$ 0. Emendas de bancada, de comissão e de relator não têm um autor só e não
        entram. As emendas somam mandatos anteriores de quem se reelegeu. Ter voto numa cidade e enviar emenda a ela
        são dois fatos; a página não diz que um explica o outro.
      </p>

      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">Votos: {dados.votos_fonte_nome}.</p>
        <FonteRodape fonte={dados.emendas_fonte_nome} url={dados.emendas_fonte_url} atualizadoEm={dados.atualizado_em} />
      </div>
    </section>
  );
}
