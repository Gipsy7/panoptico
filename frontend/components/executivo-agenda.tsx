import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import type { Agenda } from "@/lib/api";
import { formatarData } from "@/lib/formato";

const TIPOS: [string, string][] = [
  ["reuniao", "Reunião"],
  ["evento", "Evento"],
  ["audiencia", "Audiência"],
  ["audiencia_publica", "Audiência pública"],
  ["viagem", "Viagem"],
  ["presente", "Presente"],
];

const ANO_ATUAL = new Date().getFullYear();
const ANOS = Array.from({ length: ANO_ATUAL - 2022 + 1 }, (_, i) => ANO_ATUAL - i);

const hora = (h: string | null) => (h ? h.slice(0, 5) : null);

/** Agenda de compromissos (e-Agendas, CGU): quem se reuniu com o agente público, e sobre o quê. */
export function AgendaSecao({
  dados,
  candidaturaId,
  tipo,
  ano,
}: {
  dados: Agenda;
  candidaturaId: number;
  tipo?: string;
  ano?: string;
}) {
  const paginas = Math.max(1, Math.ceil(dados.total / dados.por_pagina));
  const link = (pagina: number) => {
    const params = new URLSearchParams();
    if (tipo) params.set("agenda_tipo", tipo);
    if (ano) params.set("agenda_ano", ano);
    params.set("agenda_pagina", String(pagina));
    return `/eleito/${candidaturaId}?${params}#ver-agenda`;
  };
  return (
    <section aria-labelledby="agenda-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="agenda-titulo" className="text-2xl">
          Agenda de compromissos
        </h2>
        <p className="text-xs text-muted-foreground">
          Reuniões, eventos, audiências e viagens que o agente público declarou (e-Agendas, da Controladoria-Geral da
          União)
        </p>
      </div>

      <form method="get" action={`/eleito/${candidaturaId}#ver-agenda`} className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-1">
          <span className="text-muted-foreground">Tipo</span>
          <select name="agenda_tipo" defaultValue={tipo ?? ""} className="alvo-link rounded-md bg-card px-2 py-1.5 ring-1 ring-foreground/20">
            <option value="">Todos</option>
            {TIPOS.map(([v, r]) => (
              <option key={v} value={v}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-muted-foreground">Ano</span>
          <select name="agenda_ano" defaultValue={ano ?? ""} className="alvo-link rounded-md bg-card px-2 py-1.5 ring-1 ring-foreground/20">
            <option value="">Todos</option>
            {ANOS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="alvo-link rounded-md px-3 py-1.5 font-medium underline underline-offset-4">
          Filtrar
        </button>
      </form>

      <p className="text-sm text-muted-foreground">
        <span className="tabular-nums">{dados.total.toLocaleString("pt-BR")}</span>{" "}
        {dados.total === 1 ? "registro" : "registros"}
      </p>

      {dados.itens.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum registro com esse filtro.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {dados.itens.map((i) => (
            <li key={`${i.tipo}-${i.id_registro}`} className="flex min-w-0 flex-col gap-1 rounded-xl bg-card p-3 ring-1 ring-foreground/10">
              <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <span className="pilula">{i.rotulo}</span>
                {i.data_inicio && (
                  <span className="tabular-nums">
                    {formatarData(i.data_inicio)}
                    {hora(i.hora_inicio) && ` às ${hora(i.hora_inicio)}`}
                  </span>
                )}
              </p>
              {i.assunto && <p className="break-words">{i.assunto}</p>}
              {(i.cargo || i.orgao) && (
                <p className="text-xs text-muted-foreground">{[i.cargo, i.orgao].filter(Boolean).join(" · ")}</p>
              )}
              {(i.local || i.destino) && (
                <p className="text-sm text-muted-foreground">
                  Local: {i.local ?? [i.origem, i.destino].filter(Boolean).join(" → ")}
                </p>
              )}
              {i.participantes_publicos.length > 0 && (
                <p className="text-sm">
                  <span className="text-muted-foreground">Agentes públicos: </span>
                  {i.participantes_publicos.map((p) => p.nome).join(", ")}
                  {i.n_participantes_publicos > i.participantes_publicos.length &&
                    ` e mais ${i.n_participantes_publicos - i.participantes_publicos.length}`}
                </p>
              )}
              {i.entidades_privadas.length > 0 && (
                <p className="text-sm">
                  <span className="text-muted-foreground">Entidades privadas: </span>
                  {i.entidades_privadas.join(", ")}
                </p>
              )}
              <a
                href={i.url}
                target="_blank"
                rel="noopener noreferrer"
                className="alvo-link self-start text-xs underline underline-offset-2"
              >
                Ver o registro na fonte
              </a>
            </li>
          ))}
        </ul>
      )}

      {paginas > 1 && (
        <nav aria-label="Páginas da agenda" className="flex items-center justify-between pt-2 text-sm">
          {dados.pagina > 1 ? (
            <Link href={link(dados.pagina - 1)} className="alvo-link font-medium underline underline-offset-4">
              ← Mais recentes
            </Link>
          ) : (
            <span />
          )}
          <span className="text-muted-foreground">
            {dados.pagina} de {paginas}
          </span>
          {dados.pagina < paginas ? (
            <Link href={link(dados.pagina + 1)} className="alvo-link font-medium underline underline-offset-4">
              Mais antigos →
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}

      {dados.nota && <p className="text-xs text-muted-foreground">{dados.nota}</p>}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
