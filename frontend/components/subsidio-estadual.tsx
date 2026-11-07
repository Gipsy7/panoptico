import { FonteRodape } from "@/components/fonte-rodape";
import { PorQueFalta } from "@/components/por-que-falta";
import type { VereadorDetalhe } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { TermoOficial } from "@/components/termo-oficial";
import { TetoDeputadoEstadual } from "@/components/teto-salarial";

/** Salário bruto (subsídio) de deputado estadual: o mesmo para toda a Assembleia, fixado em lei estadual. */
export function SubsidioEstadualSecao({ v }: { v: VereadorDetalhe }) {
  const s = v.subsidio;
  if (!s) return null;
  const cargo = v.uf === "DF" ? "deputados distritais" : "deputados estaduais";
  const casa = v.uf === "DF" ? "Câmara Legislativa" : "Assembleia Legislativa";
  return (
    <section aria-labelledby="salario-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="salario-titulo" className="text-2xl">
          Salário bruto (subsídio)
        </h2>
        <p className="text-sm text-muted-foreground">
          <TermoOficial id="subsidio">Subsídio</TermoOficial> mensal, valor fixado em lei
        </p>
      </div>
      {s.valor !== null ? (
        <>
          <div className="figura">
            <p className="text-sm text-muted-foreground">Valor bruto por mês, antes dos descontos</p>
            <p className="numero text-3xl">{formatarReais(s.valor)}</p>
            {s.vigente_desde && (
              <p className="text-sm text-muted-foreground">Desde {formatarData(s.vigente_desde)}</p>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            O valor é o mesmo para todos os {cargo} da {casa}, por isso não há média para comparar.
            Os gastos do gabinete e as demais verbas são outro dinheiro e não fazem parte do salário.
          </p>
          {s.ato_normativo && (
            <p className="text-sm text-muted-foreground">
              Ato que fixa o valor: <span className="text-xs">{s.ato_normativo}</span>
            </p>
          )}
          {s.observacao && <p className="text-sm text-muted-foreground">{s.observacao}</p>}
          <FonteRodape fonte={s.ato_normativo ?? casa} url={s.fonte_url ?? undefined} atualizadoEm={s.consultado_em} />
          <h3 className="text-base font-semibold">Valor pago e teto da Constituição</h3>
          <TetoDeputadoEstadual uf={v.uf} subsidio={s} nomeCasa={casa} />
        </>
      ) : (
        <>
          <p className="text-sm">
            O valor do salário dos {cargo} desta {casa} ainda não está no site: o ato que o fixa não foi
            conferido em fonte oficial. Não estimamos nem calculamos o valor.
          </p>
          {s.observacao && <p className="text-sm text-muted-foreground">{s.observacao}</p>}
          <PorQueFalta uf={v.uf} />
          <h3 className="text-base font-semibold">Teto da Constituição</h3>
          <TetoDeputadoEstadual uf={v.uf} subsidio={s} nomeCasa={casa} />
        </>
      )}
    </section>
  );
}
