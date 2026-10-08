import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { VotosComissoes } from "@/lib/api";
import { formatarData } from "@/lib/formato";

/** Votos nas votações nominais das comissões: só a lista, sem percentual (ver DECISOES). */
export function ComissoesSecao({ dados, parlamentarId }: { dados: VotosComissoes; parlamentarId: number }) {
  if (dados.total === 0) return null;
  const paginas = Math.ceil(dados.total / dados.por_pagina);
  const link = (pagina: number) => `/parlamentar/${parlamentarId}?pagina_comissoes=${pagina}#comissoes-titulo`;

  return (
    <section aria-labelledby="comissoes-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="comissoes-titulo" className="text-2xl">
          Votos nas comissões
        </h2>
        <p className="text-xs text-muted-foreground">
          Votações nominais nas comissões, onde os projetos são discutidos antes do Plenário
        </p>
      </div>
      <p className="text-sm">
        Votou em <span className="numero text-lg">{dados.total}</span>{" "}
        {dados.total === 1 ? "votação nominal" : "votações nominais"} de comissão, em:
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {dados.comissoes.map((c) => (
          <li key={c.sigla} className="pilula" title={c.nome ?? c.sigla}>
            {c.sigla} · {c.votacoes}
          </li>
        ))}
      </ul>

      <details className="painel" open={dados.pagina > 1}>
        <summary className="cursor-pointer font-medium">Ver os votos, dos mais recentes</summary>
        <ul className="mt-3 lista-fios flex flex-col">
          {dados.itens.map((v, i) => (
            <li key={`${v.data}-${i}`} className="flex flex-col gap-1 py-3">
              <span className="text-xs text-muted-foreground">
                {formatarData(v.data)} · {v.orgao_nome ?? v.orgao_sigla}
              </span>
              {v.proposicao &&
                (v.url ? (
                  <a href={v.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                    {v.proposicao}
                  </a>
                ) : (
                  <span className="font-medium">{v.proposicao}</span>
                ))}
              {v.proposicao_ementa && <p className="line-clamp-2 text-sm">{v.proposicao_ementa}</p>}
              <p className="line-clamp-2 text-xs text-muted-foreground">{v.descricao}</p>
              <p className="text-sm">
                Votou: <span className="font-semibold">{v.voto || "Sem voto registrado"}</span>
              </p>
            </li>
          ))}
        </ul>
        {paginas > 1 && (
          <nav aria-label="Páginas dos votos nas comissões" className="mt-3 flex items-center justify-between text-sm">
            {dados.pagina > 1 ? (
              <Link href={link(dados.pagina - 1)} className="underline underline-offset-4">
                ← Mais recentes
              </Link>
            ) : (
              <span />
            )}
            <span className="text-muted-foreground">
              {dados.pagina} de {paginas}
            </span>
            {dados.pagina < paginas ? (
              <Link href={link(dados.pagina + 1)} className="underline underline-offset-4">
                Mais antigas →
              </Link>
            ) : (
              <span />
            )}
          </nav>
        )}
      </details>
      <p className="text-xs text-muted-foreground">
        Cada parlamentar vota só nas comissões de que faz parte, então aqui não há percentual nem
        comparação com a média: a presença e o alinhamento contam só o Plenário.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
