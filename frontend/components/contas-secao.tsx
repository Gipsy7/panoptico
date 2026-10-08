import { FonteRodape } from "@/components/fonte-rodape";
import type { ContasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

/** Contas anuais da prefeitura (SICONFI): quanto arrecadou e em que áreas gastou. */
export function ContasSecao({ dados, cidade }: { dados: ContasMunicipio; cidade: string }) {
  const maior = dados.por_area[0]?.valor ?? 0;
  return (
    <section aria-labelledby="contas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="contas-titulo" className="text-2xl">
          Contas de {cidade} em {dados.ano}
        </h2>
        <p className="text-xs text-muted-foreground">
          O que a prefeitura declarou ao Tesouro Nacional (Declaração de Contas Anuais)
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        {dados.receita_total != null && (
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Arrecadou</dt>
            <dd className="numero text-3xl">{formatarReais(dados.receita_total, true)}</dd>
          </div>
        )}
        {dados.despesa_paga != null && (
          <div className="figura">
            <dt className="text-sm text-muted-foreground">Gastou (pago)</dt>
            <dd className="numero text-3xl">{formatarReais(dados.despesa_paga, true)}</dd>
            {dados.despesa_por_habitante != null && (
              <dd className="text-xs text-muted-foreground">
                {formatarReais(dados.despesa_por_habitante, true)} por habitante
              </dd>
            )}
          </div>
        )}
      </dl>
      {dados.camara != null && dados.despesa_paga ? (
        <p className="text-sm">
          A câmara municipal custou{" "}
          <span className="numero text-lg">{formatarReais(dados.camara, true)}</span>
          <span className="text-muted-foreground">
            {" "}
            ({((dados.camara / dados.despesa_paga) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% do
            que a cidade gastou)
          </span>
        </p>
      ) : null}
      {dados.por_area.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Em que áreas gastou</h3>
          <ul className="flex flex-col gap-2.5">
            {dados.por_area.map((a) => (
              <li key={a.nome} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0">{a.nome}</span>
                  <span className="shrink-0 tabular-nums">
                    {formatarReais(a.valor, true)}
                    <span className="ml-1 text-xs text-muted-foreground">
                      {a.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%
                    </span>
                  </span>
                </div>
                <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
                  <div
                    className="h-1.5 rounded-full bg-chart-1"
                    style={{ width: `${maior ? Math.max(1, (a.valor / maior) * 100) : 0}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Valores pagos no ano, pela função de governo (a classificação oficial do orçamento).
        &quot;Encargos especiais&quot; inclui dívida e transferências; &quot;Legislativa&quot; é a câmara.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
