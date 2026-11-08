import { FonteRodape } from "@/components/fonte-rodape";
import type { AgroMunicipio } from "@/lib/api";
import { formatarReaisCompacto } from "@/lib/formato";

/**
 * Agro em "Por dentro da cidade" (IBGE, Produção Agrícola Municipal): o valor da produção das lavouras no último
 * ano e os produtos que mais pesam, cada um com a parte do total da cidade; e a criação (Pesquisa
 * da Pecuária Municipal): rebanhos em cabeças e o valor de leite, ovos, mel. A PPM não mede carne.
 */
export function AgroResumo({ dados, cidade, uf }: { dados: AgroMunicipio; cidade: string; uf: string }) {
  if ((dados.valor_total == null || dados.ano == null) && !dados.pecuaria) return null;
  if (dados.valor_total == null || dados.ano == null) {
    return dados.pecuaria ? <Criacao p={dados.pecuaria} cidade={cidade} /> : null;
  }
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
      <p className="text-xs text-muted-foreground">Termo oficial: valor da produção agrícola (lavouras temporárias e permanentes).</p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
      {dados.pecuaria && <Criacao p={dados.pecuaria} cidade={cidade} />}
    </div>
  );
}

type Pecuaria = NonNullable<AgroMunicipio["pecuaria"]>;

/** Criação: rebanhos (cabeças) e o valor da produção de origem animal. */
function Criacao({ p, cidade }: { p: Pecuaria; cidade: string }) {
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-4">
      <h3 className="text-base font-semibold">Criação em {cidade}, {p.ano}</h3>
      {p.valor_origem_animal != null && (
        <p className="text-sm">
          Leite, ovos, mel e outros produtos de origem animal:{" "}
          <span className="numero text-lg">{formatarReaisCompacto(p.valor_origem_animal)}</span>
        </p>
      )}
      {p.produtos.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm">
          {p.produtos.slice(0, 5).map((x) => (
            <li key={x.produto} className="flex flex-wrap justify-between gap-x-3">
              <span>{x.produto}</span>
              <span className="tabular-nums text-muted-foreground">{formatarReaisCompacto(x.valor)}</span>
            </li>
          ))}
        </ul>
      )}
      {p.rebanhos.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
          {p.rebanhos.slice(0, 8).map((r) => (
            <div key={r.item}>
              <dt className="text-xs text-muted-foreground">{r.item}</dt>
              <dd className="numero">{r.cabecas.toLocaleString("pt-BR")} cabeças</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-xs text-muted-foreground">
        Rebanhos em número de cabeças (termo oficial: efetivo dos rebanhos). A pesquisa não mede carne nem abate.
      </p>
      <FonteRodape fonte={p.fonte_nome} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </div>
  );
}
