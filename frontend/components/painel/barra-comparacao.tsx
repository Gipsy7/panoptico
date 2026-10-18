/**
 * Duas barras na MESMA escala: a da pessoa (ou cidade) em bronze e a da média em cinza.
 * Os valores ficam escritos ao lado de cada rótulo; as barras são só reforço visual
 * (aria-hidden), então o leitor de tela lê "Fulano 6% · Média da Câmara 79%".
 *
 * Uso:
 *   <BarraComparacao
 *     pessoa={{ rotulo: "Arthur Lira", valor: 5.7 }}
 *     media={{ rotulo: "Média da Câmara", valor: 78.8 }}
 *     formato="percentual"
 *     escala={100}            // opcional; padrão = o maior dos dois valores
 *   />
 * Sem nota nem cor de bom/ruim: bronze é sempre a pessoa, cinza é sempre a média.
 */
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

export type FormatoNumero = "reais" | "reais-compacto" | "inteiro" | "decimal" | "percentual";

const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function formatarNumero(valor: number, formato: FormatoNumero): string {
  switch (formato) {
    case "reais":
      return formatarReais(valor, true);
    case "reais-compacto":
      return formatarReaisCompacto(valor);
    case "inteiro":
      return INTEIRO.format(valor);
    case "decimal":
      return DECIMAL.format(valor);
    case "percentual":
      return `${DECIMAL.format(valor)}%`;
  }
}

type Lado = { rotulo: string; valor: number };

export function BarraComparacao({
  pessoa,
  media,
  formato,
  escala,
}: {
  pessoa: Lado;
  media: Lado;
  formato: FormatoNumero;
  escala?: number;
}) {
  const maximo = Math.max(escala ?? 0, pessoa.valor, media.valor);
  const largura = (v: number) => (maximo > 0 ? `${Math.max(0, (v / maximo) * 100)}%` : "0%");
  return (
    <div className="flex min-w-0 flex-col gap-1.5 text-sm">
      {[
        { lado: pessoa, cor: "bg-bronze" },
        { lado: media, cor: "bg-chart-3" },
      ].map(({ lado, cor }) => (
        <div key={cor} className="flex min-w-0 flex-col gap-0.5">
          <p className="flex min-w-0 items-baseline justify-between gap-2">
            <span className="min-w-0 truncate text-muted-foreground">{lado.rotulo}</span>
            <span className="shrink-0 tabular-nums">{formatarNumero(lado.valor, formato)}</span>
          </p>
          <div aria-hidden className="h-2 w-full overflow-hidden rounded-[2px] bg-muted">
            <div className={`h-full rounded-[2px] ${cor}`} style={{ width: largura(lado.valor) }} />
          </div>
        </div>
      ))}
    </div>
  );
}
