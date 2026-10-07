import Form from "next/form";
import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { Casa, Placar, Votos } from "@/lib/api";
import { CASA_CURTA, formatarData } from "@/lib/formato";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function VotosSecao({
  dados,
  casa,
  parlamentarId,
}: {
  dados: Votos;
  casa: Casa;
  parlamentarId: number;
}) {
  const paginas = Math.max(1, Math.ceil(dados.total / dados.por_pagina));
  const link = (pagina: number) => {
    const params = new URLSearchParams({ ano: String(dados.ano), pagina_votos: String(pagina) });
    if (dados.tema) params.set("tema", dados.tema);
    return `/parlamentar/${parlamentarId}?${params}#votos-titulo`;
  };

  return (
    <section aria-labelledby="votos-titulo" className="flex flex-col gap-4">
      <div>
        <h2 id="votos-titulo" className="text-xl font-semibold">
          Como votou
        </h2>
        <p className="text-xs text-muted-foreground">
          Votações nominais do Plenário em {dados.ano}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3">
        {dados.governo && (
          <Bloco
            rotulo="Votou como o Governo orientou"
            placar={dados.governo}
            media={dados.media_governo}
            casa={casa}
          />
        )}
        <Bloco
          rotulo="Votou como a maioria do seu partido"
          placar={dados.partido}
          media={dados.media_partido}
          casa={casa}
        />
      </dl>
      <p className="text-sm text-muted-foreground">
        Contam só as votações em que deu voto (Sim, Não, Abstenção ou Obstrução).
        {dados.governo &&
          " Para o Governo, só quando a liderança do Governo orientou Sim, Não ou Obstrução; votações liberadas ficam de fora."}
        {casa === "senado" &&
          " No Senado, a maioria das votações é secreta ou não tem orientação registrada, por isso os totais são pequenos."}{" "}
        A maioria do partido é como votaram os outros {casa === "camara" ? "deputados" : "senadores"} do
        mesmo partido naquele dia.{" "}
        <Link href="/sobre-as-fontes" className="underline underline-offset-2">
          Como calculamos
        </Link>
      </p>

      {dados.temas_disponiveis.length > 0 && (
        <Form action={`/parlamentar/${parlamentarId}`} className="flex flex-wrap items-end gap-2">
          <input type="hidden" name="ano" value={dados.ano} />
          <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
            Filtrar por tema
            <select
              name="tema"
              defaultValue={dados.tema ?? ""}
              className="h-11 rounded-xl border border-input bg-card px-3 text-sm focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              <option value="">Todos os temas</option>
              {dados.temas_disponiveis.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            className="h-11 rounded-xl bg-secondary px-4 text-sm font-medium text-secondary-foreground"
          >
            Filtrar
          </button>
        </Form>
      )}

      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">
          {dados.total} {dados.total === 1 ? "votação" : "votações"}
          {dados.tema && ` sobre ${dados.tema}`}
        </p>
        <ul className="flex flex-col divide-y rounded-xl bg-card ring-1 ring-foreground/10">
          {dados.itens.map((v, i) => (
            <li key={`${v.data}-${i}`} className="flex flex-col gap-2 p-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-muted-foreground">{formatarData(v.data)}</span>
                {v.proposicao &&
                  (v.url ? (
                    <a
                      href={v.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium underline underline-offset-2"
                    >
                      {v.proposicao}
                    </a>
                  ) : (
                    <span className="font-medium">{v.proposicao}</span>
                  ))}
                {v.proposicao_ementa && <p className="line-clamp-3 text-sm">{v.proposicao_ementa}</p>}
                {v.temas.length > 0 && (
                  <p className="text-xs text-muted-foreground">{v.temas.join(" · ")}</p>
                )}
              </div>
              <p className="line-clamp-2 text-xs text-muted-foreground">{v.descricao}</p>
              <dl className="grid grid-cols-3 gap-2 text-xs">
                <Voto rotulo="Votou" valor={v.voto || "Sem voto registrado"} destaque />
                <Voto rotulo="Governo orientou" valor={v.orientacao_governo} />
                <Voto rotulo={`Maioria ${v.partido ?? "do partido"}`} valor={v.maioria_partido} />
              </dl>
            </li>
          ))}
        </ul>
        {paginas > 1 && (
          <nav aria-label="Páginas de votações" className="flex items-center justify-between pt-2 text-sm">
            {dados.pagina > 1 ? (
              <Link href={link(dados.pagina - 1)} className="font-medium underline underline-offset-4">
                ← Mais recentes
              </Link>
            ) : (
              <span />
            )}
            <span className="text-muted-foreground">
              {dados.pagina} de {paginas}
            </span>
            {dados.pagina < paginas ? (
              <Link href={link(dados.pagina + 1)} className="font-medium underline underline-offset-4">
                Mais antigas →
              </Link>
            ) : (
              <span />
            )}
          </nav>
        )}
      </div>

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

function Bloco({
  rotulo,
  placar,
  media,
  casa,
}: {
  rotulo: string;
  placar: Placar;
  media: number | null;
  casa: Casa;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="text-2xl font-bold tabular-nums">
        {placar.total ? `${placar.iguais} de ${placar.total}` : "—"}
      </dd>
      {placar.percentual !== null && (
        <dd className="text-sm text-muted-foreground tabular-nums">
          {PCT.format(placar.percentual)}%
          {media !== null && ` · média do ${CASA_CURTA[casa]} ${PCT.format(media)}%`}
        </dd>
      )}
    </div>
  );
}

function Voto({ rotulo, valor, destaque }: { rotulo: string; valor: string | null; destaque?: boolean }) {
  return (
    <div className={destaque ? "rounded-md bg-accent px-2 py-1" : "px-2 py-1"}>
      <dt className="text-muted-foreground">{rotulo}</dt>
      <dd className="font-semibold">{valor || "—"}</dd>
    </div>
  );
}
