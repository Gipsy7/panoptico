import { FonteRodape } from "@/components/fonte-rodape";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import type { ContasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

const VISIVEIS = 4;

/** Quanto a câmara municipal custou por morador, ao lado da média simples do estado. */
function CamaraPorMorador({ dados, cidade }: { dados: ContasMunicipio; cidade: string }) {
  const porMorador = dados.camara_por_habitante;
  const media = dados.media_uf_camara_por_habitante;
  const naMedia = dados.municipios_na_media_camara ?? 0;
  const sem = dados.municipios_sem_camara ?? 0;
  if (media == null && porMorador == null) return null;
  const rotuloMedia = `Média dos ${naMedia.toLocaleString("pt-BR")} municípios do estado`;
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <h3 className="font-medium">Quanto a câmara custou por morador</h3>
      <p className="text-sm text-muted-foreground">
        Gasto da câmara municipal (função <span lang="pt-BR">Legislativa</span>) em {dados.ano}, dividido pela população
      </p>
      {porMorador != null && media != null ? (
        <>
          <BarraComparacao
            pessoa={{ rotulo: cidade, valor: porMorador }}
            media={{ rotulo: rotuloMedia, valor: media }}
            formato="reais"
          />
          <p className="text-sm tabular-nums">
            Conta: {formatarReais(dados.camara!)} ÷ {dados.populacao!.toLocaleString("pt-BR")} moradores ={" "}
            {formatarReais(porMorador)} por morador.
          </p>
        </>
      ) : porMorador == null ? (
        <>
          <p className="numero text-xl">Não informado</p>
          <p className="text-sm">
            A prefeitura entregou as contas de {dados.ano} sem separar o gasto da câmara, por isso não há o valor por
            morador.
          </p>
          {media != null && (
            <p className="text-sm text-muted-foreground">
              {rotuloMedia}: <span className="tabular-nums">{formatarReais(media, true)}</span> por morador.
            </p>
          )}
        </>
      ) : null}
      <details className="painel">
        <summary className="cursor-pointer text-sm font-medium">Como é calculada a média</summary>
        <div className="mt-2 flex flex-col gap-2 text-sm text-muted-foreground">
          <p>
            Média simples: para cada município do estado, o gasto da câmara dividido pela população; depois, a média
            desses {naMedia.toLocaleString("pt-BR")} valores. Cada cidade conta um, grande ou pequena. É a mesma
            conta e a mesma população do gasto da prefeitura por morador, acima.
          </p>
          {sem > 0 && (
            <p>
              Ficam de fora {sem.toLocaleString("pt-BR")} {sem === 1 ? "município" : "municípios"} que entregaram as
              contas de {dados.ano} sem separar o gasto da câmara.
            </p>
          )}
        </div>
      </details>
    </div>
  );
}

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
          <div aria-hidden className="h-1.5 w-full rounded-[1px] bg-muted">
            <div
              className="h-1.5 rounded-[1px] bg-chart-1"
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
      <CamaraPorMorador dados={dados} cidade={cidade} />
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
