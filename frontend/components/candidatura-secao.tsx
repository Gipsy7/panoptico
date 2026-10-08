import { FonteRodape } from "@/components/fonte-rodape";
import type { CandidaturaTse } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const LIMITE_VISIVEL = 8;

/** Bens declarados ao TSE e contas da campanha que deu o mandato atual. Os dados pessoais
 * ficam em "Quem é" (QuemESecao), no topo do perfil. */
export function CandidaturaSecao({
  dados,
}: {
  dados: Pick<CandidaturaTse, "bens" | "campanha" | "fonte_nome" | "fonte_url" | "atualizado_em">;
}) {
  const { bens, campanha } = dados;
  if (!bens && !campanha) return null;

  return (
    <section aria-labelledby="tse-titulo" className="revelar flex flex-col gap-6">
      <div>
        <h2 id="tse-titulo" className="text-2xl">
          Eleição
        </h2>
        <p className="text-xs text-muted-foreground">
          Declarados pelo próprio candidato à Justiça Eleitoral (TSE)
        </p>
      </div>

      {bens && (
        <div className="flex flex-col gap-3">
          <h3 className="font-medium">
            Bens declarados na eleição de {bens.candidatura.ano}
            <span className="block text-xs font-normal text-muted-foreground">
              candidatura a {bens.candidatura.cargo.toLowerCase()} · {bens.candidatura.unidade}
            </span>
          </h3>
          <dl className="grid grid-cols-2 gap-3">
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Total declarado</dt>
              <dd className="numero text-3xl">{formatarReais(bens.total, true)}</dd>
              <dd className="text-xs text-muted-foreground">
                {bens.quantidade} {bens.quantidade === 1 ? "bem" : "bens"}
              </dd>
            </div>
            {bens.anterior && (
              <div className="figura">
                <dt className="text-sm text-muted-foreground">
                  Na eleição anterior ({bens.anterior.candidatura.ano})
                </dt>
                <dd className="numero text-3xl">{formatarReais(bens.anterior.total, true)}</dd>
                <dd className="text-xs text-muted-foreground">
                  candidatura a {bens.anterior.candidatura.cargo.toLowerCase()}
                </dd>
              </div>
            )}
          </dl>
          {bens.itens.length > 0 && (
            <details className="painel">
              <summary className="cursor-pointer font-medium">
                Ver os bens declarados{bens.quantidade > bens.itens.length ? ` (os ${bens.itens.length} de maior valor)` : ""}
              </summary>
              <ul className="mt-3 lista-fios flex flex-col">
                {bens.itens.map((b, i) => (
                  <li key={i} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                    <span className="min-w-0">
                      <span className="block">{b.tipo}</span>
                      {b.descricao && (
                        <span className="block text-xs text-muted-foreground">{b.descricao}</span>
                      )}
                    </span>
                    <span className="shrink-0 tabular-nums">{formatarReais(b.valor, true)}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          <p className="text-xs text-muted-foreground">
            Valores como o candidato declarou, sem correção pela inflação. Bens costumam ser
            declarados pelo valor de compra, que pode ser bem menor que o de mercado.{" "}
            <a href={bens.fonte_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
              Arquivo oficial
            </a>
          </p>
        </div>
      )}

      {campanha && (
        <div className="flex flex-col gap-3">
          <h3 className="font-medium">
            Campanha de {campanha.candidatura.ano}
            <span className="block text-xs font-normal text-muted-foreground">
              a que deu o mandato atual · {campanha.candidatura.cargo.toLowerCase()} · {campanha.candidatura.unidade}
            </span>
          </h3>
          <dl className="grid grid-cols-2 gap-3">
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Arrecadou</dt>
              <dd className="numero text-3xl">{formatarReais(campanha.receitas_total, true)}</dd>
            </div>
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Gastou (contratado)</dt>
              <dd className="numero text-3xl">{formatarReais(campanha.despesas_total, true)}</dd>
            </div>
          </dl>
          <Partes titulo="De onde veio o dinheiro" itens={campanha.receitas_por_origem} total={campanha.receitas_total} />
          <p className="text-xs text-muted-foreground">
            &quot;Fundo eleitoral&quot; e &quot;fundo partidário&quot; são dinheiro público repassado pelos
            partidos. {campanha.numero_doadores > 0 &&
              `${campanha.numero_doadores} ${campanha.numero_doadores === 1 ? "pessoa doou" : "pessoas doaram"}; não mostramos o nome de doadores, que são cidadãos comuns.`}
          </p>
          <Partes titulo="Com o que gastou" itens={campanha.despesas_por_tipo} total={campanha.despesas_total} />
        </div>
      )}

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

function Partes({ titulo, itens, total }: { titulo: string; itens: { nome: string; valor: number }[]; total: number }) {
  if (itens.length === 0 || total <= 0) return null;
  const visiveis = itens.slice(0, LIMITE_VISIVEL);
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-medium">{titulo}</h4>
      <ul className="flex flex-col gap-2.5">
        {visiveis.map((i) => {
          const parte = (i.valor / total) * 100;
          return (
            <li key={i.nome} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0">{i.nome}</span>
                <span className="shrink-0 tabular-nums">
                  {formatarReais(i.valor, true)}
                  <span className="ml-1 text-xs text-muted-foreground">
                    {parte < 0.1 ? "<0,1" : parte.toLocaleString("pt-BR", { maximumFractionDigits: parte < 1 ? 1 : 0 })}%
                  </span>
                </span>
              </div>
              <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
                <div className="h-1.5 rounded-full bg-chart-1" style={{ width: `${Math.max(1, parte)}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
