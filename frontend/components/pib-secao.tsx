import { FonteRodape } from "@/components/fonte-rodape";
import type { PibMunicipio } from "@/lib/api";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

/**
 * Economia em "Por dentro da cidade" (IBGE, PIB dos Municípios): o PIB mais recente, o PIB por morador com o do
 * estado e o do Brasil no mesmo ano, e de onde vem a riqueza (valor adicionado por atividade).
 * Valores da época, sem descontar a inflação: por isso a comparação é no mesmo ano.
 */
export function PibResumo({ dados, cidade, uf }: { dados: PibMunicipio; cidade: string; uf: string }) {
  const ultimo = dados.serie[dados.serie.length - 1];
  const comPorMorador = [...dados.serie].reverse().find((a) => a.por_habitante != null);
  if (!ultimo) return null;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">PIB de {cidade} em {ultimo.ano}</dt>
          <dd className="numero text-2xl">{formatarReaisCompacto(ultimo.pib)}</dd>
          <dd className="text-sm text-muted-foreground">Tudo o que foi produzido na cidade no ano</dd>
        </div>
        {comPorMorador?.por_habitante != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">PIB por morador em {comPorMorador.ano}</dt>
            <dd className="numero text-2xl">{formatarReais(comPorMorador.por_habitante, true)}</dd>
            <dd className="text-sm text-muted-foreground">
              {[
                comPorMorador.uf_por_habitante != null && `${uf}: ${formatarReais(comPorMorador.uf_por_habitante, true)}`,
                comPorMorador.brasil_por_habitante != null &&
                  `Brasil: ${formatarReais(comPorMorador.brasil_por_habitante, true)}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </dd>
            <dd className="text-xs text-muted-foreground">PIB dividido pela população do IBGE no mesmo ano</dd>
          </div>
        )}
      </dl>
      {dados.setores && (
        <div className="flex flex-col gap-2">
          <h3 className="text-base font-semibold">De onde vem a riqueza, em {dados.setores.ano}</h3>
          <ul className="flex flex-col gap-2.5">
            {dados.setores.itens.map((s) => (
              <li key={s.setor} className="flex flex-col gap-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
                  <span className="min-w-0">{s.setor}</span>
                  <span className="flex flex-wrap gap-x-1 tabular-nums">
                    {s.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%
                    <span className="text-muted-foreground">{formatarReaisCompacto(s.valor)}</span>
                  </span>
                </div>
                <div aria-hidden className="h-1.5 w-full rounded-[1px] bg-muted">
                  <div
                    className="h-1.5 rounded-[1px]"
                    style={{ width: `${Math.max(1, s.percentual)}%`, background: "var(--tema-economia)" }}
                  />
                </div>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Termo oficial: valor adicionado bruto por atividade. O ano mais recente do IBGE com a divisão por atividade
            pode ser anterior ao do PIB total.
          </p>
        </div>
      )}
      <p className="text-sm text-muted-foreground">
        Valores da época, sem descontar a inflação: compare com o estado e o Brasil no mesmo ano, não ao longo do
        tempo.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
