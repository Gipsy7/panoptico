import { TermoOficial } from "@/components/termo-oficial";
import { TetoVereador } from "@/components/teto-salarial";
import type { VereadorDetalhe } from "@/lib/api";

/** Seção "Salário bruto (subsídio)" do vereador: o teto da cidade e a falta do valor pago. */
export function TetoVereadorSecao({ v, nomeCasa }: { v: VereadorDetalhe; nomeCasa: string }) {
  if (!v.populacao) return null;
  const cidade = v.municipio_nome ?? "A cidade";
  return (
    <section aria-labelledby="salario-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="salario-titulo" className="text-2xl">
          Salário bruto (subsídio)
        </h2>
        <p className="text-sm text-muted-foreground">
          <TermoOficial id="subsidio">Subsídio</TermoOficial> mensal: o teto que a Constituição fixa para a cidade
        </p>
      </div>
      <TetoVereador
        cidade={cidade}
        uf={v.uf}
        populacao={v.populacao}
        subsidioUf={v.subsidio_uf}
        nomeCasa={`${nomeCasa} de ${cidade}`}
      />
    </section>
  );
}
