import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import { ListaResumida } from "@/components/painel/lista-resumida";
import type { Casa, VotosPorTema } from "@/lib/api";
import { formatarData } from "@/lib/formato";

const LIMITE = 6;
const DA_CASA: Record<Casa, string> = { camara: "da Câmara", senado: "do Senado" };

export function VotosTemaSecao({
  dados,
  casa,
  parlamentarId,
}: {
  dados: VotosPorTema;
  casa: Casa;
  parlamentarId: number;
}) {
  const itens = dados.temas.map((t) => {
    const params = new URLSearchParams({ ano: String(dados.ano), tema: t.tema });
    return (
      <li key={t.tema} className="flex flex-col gap-2 border-b border-border py-4">
        <div className="flex flex-col gap-0.5">
          <h3 className="text-base font-semibold">{t.tema}</h3>
          <p className="numero text-xl tabular-nums">
            Votou em {t.votou} de {t.total_votacoes}
          </p>
        </div>
        {t.percentual !== null && t.media_casa_percentual !== null && (
          <BarraComparacao
            pessoa={{ rotulo: "Participação neste tema", valor: t.percentual }}
            media={{ rotulo: `Média ${DA_CASA[casa]}`, valor: t.media_casa_percentual }}
            formato="percentual"
            escala={100}
          />
        )}
        {t.governo_total > 0 && (
          <p className="text-sm text-muted-foreground">
            Votou como o Governo orientou em {t.governo_iguais} de {t.governo_total}.
          </p>
        )}
        <p className="text-sm">
          <Link
            href={`/parlamentar/${parlamentarId}?${params}#votos-titulo`}
            className="alvo-link font-medium underline underline-offset-2"
          >
            Ver as votações sobre {t.tema}
          </Link>
        </p>
      </li>
    );
  });

  return (
    <section aria-labelledby="votos-tema-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="votos-tema-titulo" className="text-2xl">
          Votações por tema
        </h2>
        <p className="text-sm text-muted-foreground">
          Votações nominais do Plenário em {dados.ano}, a partir de {formatarData(dados.periodo_inicio)}
        </p>
      </div>

      {itens.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhuma votação deste período tem tema registrado pela {casa === "camara" ? "Câmara" : "Senado"}.
        </p>
      ) : (
        <ListaResumida itens={itens} limite={LIMITE} />
      )}

      <p className="text-sm text-muted-foreground">
        O tema é o que a própria Casa registrou para o projeto votado. Uma votação pode ter mais de um tema e,
        então, conta em cada um; por isso a soma dos temas pode passar do total de votações. Votações sem tema
        registrado ficam de fora. A média {DA_CASA[casa]} considera quem está em exercício; quem não votou
        no tema entra com zero.
      </p>

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
