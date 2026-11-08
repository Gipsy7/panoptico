import { FonteRodape } from "@/components/fonte-rodape";
import type { ObrasMunicipio } from "@/lib/api";
import { formatarData, formatarReaisCompacto } from "@/lib/formato";

/**
 * Obras federais da cidade (Obrasgov.br): quantas em cada situação, como o órgão registra, e a
 * lista com o valor previsto e o percentual executado. Sem juízo: a situação é a da fonte e a
 * barra é só o percentual informado.
 */

const VISIVEIS = 12;

function Linha({ o }: { o: ObrasMunicipio["itens"][number] }) {
  return (
    <li className="flex flex-col gap-1 border-t border-border py-3">
      <a href={o.url} target="_blank" rel="noopener" className="font-medium underline-offset-4 hover:underline">
        {o.nome}
      </a>
      <p className="flex flex-wrap gap-x-3 text-sm text-muted-foreground">
        {o.situacao && <span className="font-medium text-foreground">{o.situacao}</span>}
        {o.valor_previsto != null && o.valor_previsto > 0 && <span>{formatarReaisCompacto(o.valor_previsto)} previstos</span>}
        {o.data_final_prevista && <span>fim previsto: {formatarData(o.data_final_prevista)}</span>}
        {o.tipo && <span>{o.tipo}</span>}
      </p>
      {o.percentual_execucao != null && (
        <div className="flex items-center gap-2 text-sm">
          <div aria-hidden className="h-1.5 w-full max-w-60 rounded-[1px] bg-muted">
            <div
              className="h-1.5 rounded-[1px]"
              style={{ width: `${Math.min(100, Math.max(0, o.percentual_execucao))}%`, background: "var(--tema-obras)" }}
            />
          </div>
          <span className="shrink-0 tabular-nums">
            {o.percentual_execucao.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% executado
          </span>
        </div>
      )}
      {o.executor && <p className="text-xs text-muted-foreground">Quem executa: {o.executor}</p>}
    </li>
  );
}

/** Resumo do topo (aba Obras de "Por dentro da cidade"): contagem por situação. */
export function ObrasResumo({ dados, municipio }: { dados: ObrasMunicipio; municipio: string }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-lg leading-snug">
        {dados.total.toLocaleString("pt-BR")} {dados.total === 1 ? "obra ou projeto federal registrado" : "obras e projetos federais registrados"} em{" "}
        {municipio}
        {dados.valor_previsto > 0 && <>, com {formatarReaisCompacto(dados.valor_previsto)} previstos</>}.
      </p>
      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {dados.por_situacao.map((g) => (
          <div key={g.situacao} className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">{g.situacao}</dt>
            <dd className="numero text-2xl">{g.obras.toLocaleString("pt-BR")}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm">
        <a href="#ver-obras" className="underline underline-offset-4">
          Ver as obras, uma a uma
        </a>
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}

/** Seção completa ("Tudo sobre"): a lista, as primeiras à mostra e o resto num "ver todas". */
export function ObrasSecao({ dados, municipio }: { dados: ObrasMunicipio; municipio: string }) {
  if (dados.total === 0) return null;
  const primeiras = dados.itens.slice(0, VISIVEIS);
  const resto = dados.itens.slice(VISIVEIS);
  return (
    <section aria-labelledby="obras-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="obras-titulo" className="text-2xl">
          Obras federais em {municipio}
        </h2>
        <p className="text-sm text-muted-foreground">
          Como o Obrasgov.br registra: situação, valor previsto e o percentual executado informado. Primeiro as que estão
          em execução ou paradas, depois as cadastradas e as concluídas; dentro de cada uma, pelo valor.
        </p>
      </div>
      <ul className="flex flex-col">
        {primeiras.map((o) => (
          <Linha key={o.id_unico} o={o} />
        ))}
      </ul>
      {resto.length > 0 && (
        <details>
          <summary className="botao-linha cursor-pointer">Ver as outras {resto.length.toLocaleString("pt-BR")}</summary>
          <ul className="mt-2 flex flex-col">
            {resto.map((o) => (
              <Linha key={o.id_unico} o={o} />
            ))}
          </ul>
        </details>
      )}
      {dados.total > dados.itens.length && (
        <p className="text-sm text-muted-foreground">
          Mostrando {dados.itens.length.toLocaleString("pt-BR")} de {dados.total.toLocaleString("pt-BR")}; as outras estão
          na fonte.
        </p>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
