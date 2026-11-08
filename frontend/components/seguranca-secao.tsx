import { FonteRodape } from "@/components/fonte-rodape";
import type { SegurancaMunicipio } from "@/lib/api";

/**
 * Segurança em "Por dentro da cidade" (SIM/DATASUS): homicídios de moradores no último ano fechado,
 * a taxa média de 3 anos por 100 mil moradores com o estado e o Brasil, e a contagem ano a ano.
 */
const um = (n: number) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function SegurancaResumo({ dados, cidade, uf }: { dados: SegurancaMunicipio; cidade: string; uf: string }) {
  const serie = dados.cidade.serie;
  const ultimo = serie[serie.length - 1];
  if (!ultimo) return null;
  const inicioMedia = serie[Math.max(0, serie.length - 3)].ano;
  const maior = Math.max(1, ...serie.map((p) => p.homicidios));
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="border-t-2 border-foreground pt-2">
          <dt className="text-sm text-muted-foreground">Moradores mortos por homicídio em {ultimo.ano}</dt>
          <dd className="numero text-2xl">{ultimo.homicidios.toLocaleString("pt-BR")}</dd>
          {ultimo.por_100_mil != null && (
            <dd className="text-sm text-muted-foreground">{um(ultimo.por_100_mil)} a cada 100 mil moradores</dd>
          )}
        </div>
        {dados.cidade.media_3_anos_por_100_mil != null && (
          <div className="border-t-2 border-foreground pt-2">
            <dt className="text-sm text-muted-foreground">
              Por ano, a cada 100 mil moradores, de {inicioMedia} a {ultimo.ano}
            </dt>
            <dd className="numero text-2xl">{um(dados.cidade.media_3_anos_por_100_mil)}</dd>
            <dd className="text-sm text-muted-foreground">
              {[
                dados.estado.media_3_anos_por_100_mil != null &&
                  `${uf}: ${um(dados.estado.media_3_anos_por_100_mil)}`,
                dados.brasil.media_3_anos_por_100_mil != null &&
                  `Brasil: ${um(dados.brasil.media_3_anos_por_100_mil)}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </dd>
          </div>
        )}
      </dl>
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">Homicídios de moradores de {cidade}, ano a ano</h3>
        <ul className="flex flex-col gap-1">
          {serie.map((p) => (
            <li key={p.ano} className="grid grid-cols-[3rem_1fr_3.5rem] items-center gap-2 text-sm">
              <span className="numero text-muted-foreground">{p.ano}</span>
              <span className="h-2.5 bg-muted" aria-hidden>
                <span
                  className="block h-full"
                  style={{ width: `${(100 * p.homicidios) / maior}%`, background: "var(--tema-seguranca)" }}
                />
              </span>
              <span className="numero text-right">{p.homicidios.toLocaleString("pt-BR")}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="text-sm text-muted-foreground">
        Conta quem morava em {cidade} e foi morto por agressão, inclusive em ação policial, onde quer que tenha
        acontecido. Em cidades pequenas poucos casos mudam muito a taxa; por isso a média de 3 anos. O Ministério da
        Saúde fecha cada ano cerca de um ano e meio depois. Termo oficial: óbitos por agressão (CID-10 X85 a Y09) e por
        intervenção legal (Y35 e Y36).
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </div>
  );
}
