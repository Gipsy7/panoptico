/**
 * "O que disseram": discursos em Plenário sobre o projeto, por dia e agrupados pelo voto que o
 * orador registrou (Votou Sim, Votou Não, Outro registro, Falou e não registrou voto, nessa ordem).
 * O resumo é o que a própria Casa publica; o argumento completo fica no link. Nunca inferimos
 * posição pelo texto.
 */
import Link from "next/link";

import type { DiscursoNaVotacao, GrupoDiscursos } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { ordenarGruposDiscurso, rotuloGrupoDiscurso } from "@/lib/projetos";
import { LinkExterno } from "@/components/link-externo";

export const AVISO_RESUMO = "Resumo publicado pela Casa. O argumento completo está no discurso; leia no link.";

function hora(iso: string | null) {
  if (!iso || !iso.includes("T")) return null;
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
}

function ItemDiscurso({ d }: { d: DiscursoNaVotacao }) {
  const partidoUf = [d.partido, d.uf].filter(Boolean).join("-");
  const horario = hora(d.data_hora);
  return (
    <li className="flex flex-col gap-1 py-3">
      <p className="flex flex-wrap items-baseline gap-x-2">
        <Link href={`/parlamentar/${d.parlamentar_id}`} className="font-semibold underline underline-offset-2">
          {d.nome}
        </Link>
        {partidoUf && <span className="text-sm text-muted-foreground">{partidoUf}</span>}
      </p>
      {(d.fase || horario) && (
        <p className="text-sm text-muted-foreground">{[d.fase, horario && `às ${horario}`].filter(Boolean).join(" · ")}</p>
      )}
      {d.sumario ? (
        <p className="text-sm leading-relaxed">{d.sumario}</p>
      ) : (
        <p className="text-sm text-muted-foreground">A Casa não publicou resumo deste discurso.</p>
      )}
      {!d.url_texto && !d.url_video && (
        <p className="text-sm text-muted-foreground">A Casa ainda não publicou o texto integral deste discurso.</p>
      )}
      {(d.url_texto || d.url_video) && (
        <p className="flex flex-wrap gap-x-4 text-sm">
          {d.url_texto && (
            <LinkExterno href={d.url_texto} className="alvo-link font-medium underline underline-offset-4">
              Ler o discurso
            </LinkExterno>
          )}
          {d.url_video && (
            <LinkExterno href={d.url_video} className="alvo-link font-medium underline underline-offset-4">
              Ver o vídeo
            </LinkExterno>
          )}
        </p>
      )}
    </li>
  );
}

/** Grupos de um dia (ou de uma votação), já na ordem fixa; grupo vazio some. */
export function GruposDeDiscursos({ grupos }: { grupos: GrupoDiscursos[] }) {
  const lista = ordenarGruposDiscurso(grupos).filter((g) => g.discursos.length > 0);
  if (lista.length === 0) return <p className="text-sm text-muted-foreground">Nenhum discurso registrado.</p>;
  return (
    <div className="flex flex-col gap-4">
      {lista.map((g) => (
        <section key={g.chave} aria-label={rotuloGrupoDiscurso(g)} className="flex flex-col">
          <h5 className="text-base font-semibold">
            {rotuloGrupoDiscurso(g)}{" "}
            <span className="font-normal text-muted-foreground tabular-nums">({g.discursos.length})</span>
          </h5>
          <ul className="lista-fios">
            {g.discursos.map((d, i) => (
              <ItemDiscurso key={`${d.parlamentar_id}-${d.data_hora ?? d.data}-${i}`} d={d} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export function AvisoDiscursos({ extra, naoAtribuidos }: { extra?: string | null; naoAtribuidos?: number }) {
  return (
    <div className="nota flex flex-col gap-1 text-sm">
      <p>{AVISO_RESUMO}</p>
      {extra && <p className="text-muted-foreground">{extra}</p>}
      {naoAtribuidos != null && naoAtribuidos > 0 && (
        <p className="text-muted-foreground">
          {naoAtribuidos.toLocaleString("pt-BR")} {naoAtribuidos === 1 ? "discurso desses dias cita" : "discursos desses dias citam"}{" "}
          vários projetos (ou tratam de outros assuntos) e não {naoAtribuidos === 1 ? "foi atribuído" : "foram atribuídos"} a este.
        </p>
      )}
    </div>
  );
}

export function DiaDeDiscursosBloco({
  data,
  total,
  grupos,
  aberto,
}: {
  data: string;
  total: number;
  grupos: GrupoDiscursos[];
  aberto: boolean;
}) {
  return (
    <details open={aberto} className="group rounded-[var(--radius)] border border-border bg-card">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze [&::-webkit-details-marker]:hidden">
        <span className="font-semibold">{formatarData(data)}</span>
        <span className="flex items-center gap-2 text-sm text-muted-foreground tabular-nums">
          {total} {total === 1 ? "discurso" : "discursos"}
          <span aria-hidden className="transition-transform duration-200 group-open:rotate-90 motion-reduce:transition-none">
            ›
          </span>
        </span>
      </summary>
      <div className="px-4 pb-4">
        <GruposDeDiscursos grupos={grupos} />
      </div>
    </details>
  );
}
