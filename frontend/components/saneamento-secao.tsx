import { FonteRodape } from "@/components/fonte-rodape";
import type { SaneamentoMunicipio, SaneamentoValores } from "@/lib/api";

/**
 * Saneamento em "Por dentro da cidade" (Censo 2022 do IBGE): quantos domicílios em cada 100 têm
 * água da rede geral, esgoto na rede e lixo coletado, com o estado e o Brasil ao lado.
 */
const um = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const ITENS: { campo: keyof SaneamentoValores; rotulo: string; oficial: string }[] = [
  {
    campo: "agua_rede",
    rotulo: "Água encanada da rede",
    oficial: "ligação à rede geral de distribuição, usada como forma principal",
  },
  {
    campo: "esgoto_rede",
    rotulo: "Esgoto ligado à rede",
    oficial: "rede geral, rede pluvial ou fossa ligada à rede",
  },
  { campo: "lixo_coletado", rotulo: "Lixo recolhido", oficial: "lixo coletado no domicílio ou em caçamba" },
];

export function SaneamentoResumo({ dados, cidade, uf }: { dados: SaneamentoMunicipio; cidade: string; uf: string }) {
  const itens = ITENS.filter((i) => dados.cidade[i.campo] != null);
  if (itens.length === 0) return null;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {itens.map((i) => (
          <div key={i.campo} className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">{i.rotulo}</dt>
            <dd className="numero text-2xl">{um(dados.cidade[i.campo]!)}%</dd>
            <dd className="text-sm text-muted-foreground">
              {[
                dados.estado[i.campo] != null && `${uf}: ${um(dados.estado[i.campo]!)}%`,
                dados.brasil[i.campo] != null && `Brasil: ${um(dados.brasil[i.campo]!)}%`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </dd>
            <dd className="text-xs text-muted-foreground">Termo oficial: {i.oficial}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-muted-foreground">
        Em % das casas e apartamentos ocupados de {cidade} no Censo {dados.ano ?? 2022}, contados pelo IBGE de porta em
        porta. O próximo Censo trará números novos; o esgoto em fossa séptica não ligada à rede fica de fora dos
        &ldquo;ligados à rede&rdquo;.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
