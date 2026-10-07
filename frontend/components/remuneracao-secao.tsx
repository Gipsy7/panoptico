import { FonteRodape } from "@/components/fonte-rodape";
import type { ParlamentarDetalhe } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";

export function RemuneracaoSecao({ remuneracao }: { remuneracao: ParlamentarDetalhe["remuneracao"] }) {
  return (
    <section aria-labelledby="remuneracao-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="remuneracao-titulo" className="text-xl font-semibold">
          Salário
        </h2>
        <p className="text-xs text-muted-foreground">Subsídio mensal dos membros do Congresso</p>
      </div>
      <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <p className="text-sm text-muted-foreground">Valor bruto por mês</p>
        <p className="text-2xl font-bold tabular-nums">
          {formatarReais(remuneracao.subsidio_mensal)}
        </p>
        <p className="text-sm text-muted-foreground">
          Desde {formatarData(remuneracao.vigente_desde)}
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        O valor é o mesmo para todos os deputados federais e senadores. Os gastos do gabinete
        são uma verba separada, reembolsada mediante nota fiscal, e não fazem parte do salário.
      </p>
      <FonteRodape fonte={remuneracao.fonte_nome} url={remuneracao.fonte_url} />
    </section>
  );
}
