import { FonteRodape } from "@/components/fonte-rodape";
import type { ContasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const VISIVEIS = 4;

function AreasLista({ lista, maior }: { lista: ContasMunicipio["por_area"]; maior: number }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {lista.map((a) => (
        <li key={a.nome} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0">{a.nome}</span>
            <span className="shrink-0 tabular-nums">
              {formatarReais(a.valor, true)}
              <span className="ml-1 text-sm text-muted-foreground">
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
  );
}

/** Contas anuais da prefeitura (SICONFI): quanto arrecadou e em que áreas gastou. */
export function ContasSecao({ dados, cidade }: { dados: ContasMunicipio; cidade: string }) {
  const maior = dados.por_area[0]?.valor ?? 0;
  const informado = Boolean(dados.despesa_paga);
  return (
    <section aria-labelledby="contas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="contas-titulo" className="text-2xl">
          Contas de {cidade} em {dados.ano}
        </h2>
        <p className="text-sm text-muted-foreground">
          O que a prefeitura declarou ao Tesouro Nacional (Declaração de Contas Anuais)
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        {dados.receita_total != null && (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Arrecadou</dt>
            <dd className="numero text-xl break-words sm:text-3xl">{formatarReais(dados.receita_total, true)}</dd>
          </div>
        )}
        <div className="figura min-w-0">
          <dt className="text-sm text-muted-foreground">Gastou (pago)</dt>
          {informado ? (
            <>
              <dd className="numero text-xl break-words sm:text-3xl">{formatarReais(dados.despesa_paga!, true)}</dd>
              {dados.despesa_por_habitante != null && (
                <dd className="text-sm text-muted-foreground">
                  {formatarReais(dados.despesa_por_habitante, true)} por habitante
                </dd>
              )}
            </>
          ) : (
            <dd className="text-sm text-muted-foreground">Não informado pela fonte</dd>
          )}
        </div>
      </dl>
      {informado && dados.despesa_por_habitante != null && dados.media_uf_despesa_por_habitante != null && (
        <p className="text-sm text-muted-foreground">
          Média dos {dados.municipios_na_media?.toLocaleString("pt-BR")} municípios do estado:{" "}
          <span className="tabular-nums">{formatarReais(dados.media_uf_despesa_por_habitante, true)}</span> por
          habitante
          {dados.media_uf_descricao && <span className="block text-sm">{dados.media_uf_descricao}</span>}
        </p>
      )}
      {informado && dados.camara != null ? (
        <p className="text-sm">
          A câmara municipal custou{" "}
          <span className="numero text-lg">{formatarReais(dados.camara, true)}</span>
          <span className="text-muted-foreground">
            {" "}
            ({((dados.camara / dados.despesa_paga!) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% do
            que a cidade gastou)
          </span>
        </p>
      ) : null}
      {dados.por_area.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Em que áreas gastou</h3>
          <AreasLista lista={dados.por_area.slice(0, VISIVEIS)} maior={maior} />
          {dados.por_area.length > VISIVEIS && (
            <details className="painel">
              <summary className="cursor-pointer font-medium">
                Ver todas as {dados.por_area.length} áreas
              </summary>
              <div className="mt-3">
                <AreasLista lista={dados.por_area.slice(VISIVEIS)} maior={maior} />
              </div>
            </details>
          )}
        </div>
      )}
      <p className="text-sm text-muted-foreground">
        Valores pagos no ano, pela função de governo (a classificação oficial do orçamento).
        &quot;Encargos especiais&quot; inclui dívida e transferências; &quot;Legislativa&quot; é a câmara.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
