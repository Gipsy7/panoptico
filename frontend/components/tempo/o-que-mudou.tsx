"use client";

/**
 * "O que mudou" (protótipo B): frases literais tiradas das séries do lugar; tocar numa abre a
 * pergunta completa, com a série, quem governava em cada período e os números ligados (o gasto da
 * área, a taxa ao lado do estado e do Brasil). As faixas só situam no tempo: não mostram causa.
 */
import { useState } from "react";

import { corDoTema, dominioDe } from "@/components/tempo/ao-longo-do-tempo";
import { EixoAnos, FaixasGestao, LinhaSerie, PainelAno, resumoSerie, useAnoFoco } from "@/components/tempo/eixo-tempo";
import type { TempoDoLugar, SerieTempo } from "@/lib/api";
import { type Descoberta, formatarValor, gerarDescobertas } from "@/lib/descobertas";

/** O que mostrar junto de cada série na pergunta completa. */
const LIGADAS: Record<string, string[]> = {
  homicidios: ["homicidios_taxa", "gasto_seguranca_estado", "gasto_seguranca_prefeitura"],
  ideb: ["gasto_educacao_prefeitura", "gasto_educacao_estado"],
  gasto_seguranca_estado: ["homicidios_taxa"],
  gasto_saude_prefeitura: ["gasto_saude_estado"],
  gasto_saude_estado: [],
  gasto_educacao_prefeitura: ["ideb"],
  pib: [],
};

const AVISO: Record<string, string> = {
  estado: "Polícias e presídios são do governo do estado; por isso o governador aparece no fundo.",
  prefeitura: "Este serviço é da prefeitura.",
  "estado e prefeituras": "Este número junta escolas do governo do estado e das prefeituras.",
};

function ultimoComparado(s: SerieTempo, nomeEstado: string) {
  const fim = s.pontos[s.pontos.length - 1];
  if (!fim || s.comparacoes.length === 0) return null;
  const partes = s.comparacoes
    .map((c) => {
      const p = c.pontos.find((x) => x.ano === fim.ano);
      return p ? `${c.rotulo === "estado" ? nomeEstado : c.rotulo}: ${formatarValor(s, p.valor)}` : null;
    })
    .filter(Boolean);
  return partes.length ? `Em ${fim.ano}: ${formatarValor(s, fim.valor)}; ${partes.join("; ")}.` : null;
}

export function OQueMudou({ linha, lugar, nomeEstado }: { linha: TempoDoLugar; lugar: string; nomeEstado: string }) {
  const descobertas = gerarDescobertas(linha, lugar, nomeEstado);
  const [aberta, setAberta] = useState<string | null>(null);
  const [todas, setTodas] = useState(false);
  if (descobertas.length === 0) return null;
  const porId = new Map(linha.series.map((s) => [s.id, s]));
  const atual = descobertas.find((x) => x.serie === aberta) ?? null;

  return (
    <section aria-labelledby="o-que-mudou" className="flex flex-col gap-3">
      <h2 id="o-que-mudou" className="text-xl">
        O que mudou em {lugar}
      </h2>
      <ul className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {descobertas.map((x, i) => (
          <li key={x.serie} className={i >= 3 && !todas ? "hidden sm:flex" : "flex"}>
            <button
              type="button"
              aria-expanded={aberta === x.serie}
              aria-controls="pergunta-aberta"
              onClick={() => setAberta((a) => (a === x.serie ? null : x.serie))}
              className={`flex w-full flex-col gap-1 border border-l-4 border-border bg-card p-3 text-left hover:border-foreground ${
                aberta === x.serie ? "outline-2 outline-foreground" : ""
              }`}
              style={{ borderLeftColor: corDoTema(x.tema) }}
            >
              <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: corDoTema(x.tema) }}>
                {x.titulo}
              </span>
              <span className="numero text-lg leading-snug">{x.frase}</span>
              <span className="text-sm text-muted-foreground">{x.detalhe}</span>
              <span className="mt-auto pt-1 text-sm underline underline-offset-4">{x.pergunta}</span>
            </button>
          </li>
        ))}
      </ul>
      {descobertas.length > 3 && !todas && (
        <button type="button" onClick={() => setTodas(true)} className="botao-linha self-start sm:hidden">
          Mais descobertas ({descobertas.length - 3})
        </button>
      )}
      <div id="pergunta-aberta" aria-live="polite">
        {atual && <Pergunta d={atual} linha={linha} porId={porId} nomeEstado={nomeEstado} />}
      </div>
    </section>
  );
}

function Pergunta({
  d: x,
  linha,
  porId,
  nomeEstado,
}: {
  d: Descoberta;
  linha: TempoDoLugar;
  porId: Map<string, SerieTempo>;
  nomeEstado: string;
}) {
  const s = porId.get(x.serie)!;
  const dom = dominioDe(linha);
  const [foco, setFoco] = useAnoFoco();
  const ligadas = (LIGADAS[x.serie] ?? []).map((id) => porId.get(id)).filter((v): v is SerieTempo => Boolean(v));
  const curta = s.decimais <= 1 && !s.unidade.startsWith("R$");
  return (
    <div className="flex flex-col gap-3 border border-t-4 border-border bg-card p-4" style={{ borderTopColor: corDoTema(x.tema) }}>
      <h3 className="text-xl">{x.pergunta}</h3>
      <div className="flex flex-col gap-1">
        {linha.gestoes.prefeito && <FaixasGestao d={dom} gestoes={linha.gestoes.prefeito} cargo="Prefeito" foco={foco} />}
        {linha.gestoes.governador && <FaixasGestao d={dom} gestoes={linha.gestoes.governador} cargo="Governador" foco={foco} />}
        <p className="pt-1 text-sm font-semibold">
          {s.rotulo} <span className="font-normal text-muted-foreground">({s.unidade})</span>
        </p>
        <p className="text-xs text-muted-foreground">{resumoSerie(s, dom)}</p>
        <LinhaSerie d={dom} s={s} cor={corDoTema(s.tema)} todos={curta} altura={110} foco={foco} aoFocar={setFoco} nomeEstado={nomeEstado} />
        {ligadas.map((l) => (
          <div key={l.id} className="border-t border-border pt-2">
            <p className="text-sm font-semibold">
              {l.rotulo} <span className="font-normal text-muted-foreground">({l.unidade})</span>
            </p>
            <p className="text-xs text-muted-foreground">{resumoSerie(l, dom)}</p>
            <LinhaSerie d={dom} s={l} cor={corDoTema(l.tema)} foco={foco} aoFocar={setFoco} nomeEstado={nomeEstado} />
            {ultimoComparado(l, nomeEstado) && <p className="text-sm text-muted-foreground">{ultimoComparado(l, nomeEstado)}</p>}
          </div>
        ))}
        <EixoAnos d={dom} foco={foco} />
      </div>
      <PainelAno ano={foco} series={[s, ...ligadas]} gestoes={linha.gestoes} nomeEstado={nomeEstado} />
      {ultimoComparado(s, nomeEstado) && <p className="text-sm">{ultimoComparado(s, nomeEstado)}</p>}
      <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
        {AVISO[s.responsavel] && <li>{AVISO[s.responsavel]}</li>}
        {s.nota && !(AVISO[s.responsavel] ?? "").startsWith(s.nota.slice(0, 12)) && <li>{s.nota}</li>}
        <li>
          Os números andarem juntos não prova que um causa o outro, e as faixas só situam quem governava. Fonte:{" "}
          {[s, ...ligadas].map((v) => v.fonte_nome).filter((v, i, a) => a.indexOf(v) === i).join("; ")}.
        </li>
      </ul>
    </div>
  );
}
