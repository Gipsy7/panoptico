import { FonteRodape } from "@/components/fonte-rodape";
import type { AgroMunicipio } from "@/lib/api";
import { formatarReaisCompacto } from "@/lib/formato";

/**
 * Agro no Raio-X (IBGE, Produção Agrícola Municipal): o valor da produção das lavouras no último
 * ano e os produtos que mais pesam, cada um com a parte do total da cidade. Só lavouras: a
 * pecuária (rebanhos, leite) ainda não está carregada, e a tela diz isso.
 */
export function AgroResumo({ dados, cidade, uf }: { dados: AgroMunicipio; cidade: string; uf: string }) {
  if (dados.valor_total == null || dados.ano == null) return null;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Lavouras de {cidade} produziram em {dados.ano}</dt>
          <dd className="numero text-2xl">{formatarReaisCompacto(dados.valor_total)}</dd>
          {dados.uf_valor_total != null && (
            <dd className="text-sm text-muted-foreground">
              {uf}: {formatarReaisCompacto(dados.uf_valor_total)} no estado inteiro
            </dd>
          )}
        </div>
      </dl>
      {dados.produtos.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-base font-semibold">O que mais pesa, em {dados.ano}</h3>
          <ul className="flex flex-col gap-2.5">
            {dados.produtos.map((p) => (
              <li key={p.produto} className="flex flex-col gap-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                  <span className="min-w-0">{p.produto}</span>
                  <span className="flex flex-wrap gap-x-1 tabular-nums">
                    {p.percentual != null && `${p.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`}
                    <span className="text-muted-foreground">{formatarReaisCompacto(p.valor)}</span>
                  </span>
                </div>
                <div aria-hidden className="h-1.5 w-full rounded-[1px] bg-muted">
                  <div
                    className="h-1.5 rounded-[1px]"
                    style={{ width: `${Math.max(1, p.percentual ?? 0)}%`, background: "var(--tema-trabalho)" }}
                  />
                </div>
              </li>
            ))}
          </ul>
          {dados.outros_produtos > 0 && (
            <p className="text-sm text-muted-foreground">E mais {dados.outros_produtos} produtos com valor menor.</p>
          )}
        </div>
      )}
      <p className="text-sm text-muted-foreground">
        Só lavouras (temporárias e permanentes). Rebanhos, leite e outros produtos de origem animal ainda não estão
        aqui. Termo oficial: valor da produção agrícola.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
