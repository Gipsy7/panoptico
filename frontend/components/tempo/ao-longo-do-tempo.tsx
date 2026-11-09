"use client";

/**
 * Aba "Ao longo do tempo" (protótipo C): as séries do lugar empilhadas, cada uma na sua escala,
 * no mesmo eixo de anos, com prefeito e governador por período. Tocar numa gestão mostra cada
 * série no começo (último ano antes da posse) e no fim do período.
 */
import { useEffect, useRef, useState } from "react";

import {
  EixoAnos,
  FaixasGestao,
  LinhaSerie,
  PainelAno,
  type Dominio,
  nomeCurto,
  resumoSerie,
  useAnoFoco,
} from "@/components/tempo/eixo-tempo";
import type { Gestao, TempoDoLugar, SerieTempo } from "@/lib/api";
import { formatarValor } from "@/lib/descobertas";

export const corDoTema = (tema: string) => `var(--tema-${tema})`;

/** Séries ligadas de saída: as de gasto ficam como opção (são muitas). */
const PADRAO = new Set(["homicidios", "ideb", "pib", "gasto_seguranca_estado", "gasto_saude_prefeitura"]);

export function dominioDe(linha: TempoDoLugar, anos = 12): Dominio {
  const ate = linha.ano_final ?? new Date().getFullYear();
  const de = Math.max(linha.ano_inicial ?? ate - anos, ate - anos);
  return { de, ate };
}

function comecoEFim(s: SerieTempo, g: Gestao) {
  const antes = [...s.pontos].reverse().find((p) => p.ano < g.inicio);
  const dentro = s.pontos.filter((p) => p.ano >= g.inicio && p.ano <= g.fim);
  const lista = [...(antes ? [antes] : []), ...dentro];
  if (lista.length < 2) return null;
  return [lista[0], lista[lista.length - 1]] as const;
}

export function AoLongoDoTempo({ linha, lugar, nomeEstado = "estado" }: { linha: TempoDoLugar; lugar: string; nomeEstado?: string }) {
  const d = dominioDe(linha);
  const [foco, setFoco] = useAnoFoco();
  const [ligadas, setLigadas] = useState<Set<string>>(
    () => new Set(linha.series.filter((s) => PADRAO.has(s.id)).map((s) => s.id)),
  );
  const [sel, setSel] = useState<{ chave: string; g: Gestao; cargo: string } | null>(null);
  const ativas = linha.series.filter((s) => ligadas.has(s.id));
  const reserva = ativas.some((s) => s.comparacoes.length > 0);
  const alternar = (id: string) =>
    setLigadas((atual) => {
      const n = new Set(atual);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  // Escolhida uma gestão, a tela vai até o resumo dela (que fica abaixo dos gráficos).
  const resumoRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!sel) return;
    const reduzido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    resumoRef.current?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "nearest" });
  }, [sel]);
  const escolher = (cargo: string) => (chave: string, g: Gestao) =>
    setSel((atual) => (atual?.chave === chave ? null : { chave, g, cargo }));

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Passe o dedo sobre um gráfico para ver o mesmo ano em todos. Dinheiro em reais de {linha.reais_de}, já
        descontada a inflação. Marque o que quer ver:
      </p>
      <fieldset className="flex flex-wrap gap-x-4 gap-y-1">
        <legend className="sr-only">Séries mostradas</legend>
        {linha.series.map((s) => (
          <label key={s.id} className="inline-flex min-h-8 items-center gap-2 text-sm">
            <input type="checkbox" checked={ligadas.has(s.id)} onChange={() => alternar(s.id)} className="size-4 accent-[var(--bronze)]" />
            <span aria-hidden className="size-2.5" style={{ background: corDoTema(s.tema) }} />
            {s.rotulo}
          </label>
        ))}
      </fieldset>

      <div className="flex flex-col gap-1">
        {linha.gestoes.prefeito && (
          <FaixasGestao d={d} gestoes={linha.gestoes.prefeito} cargo="Prefeito" selecionada={sel?.chave} aoEscolher={escolher("Prefeito")} foco={foco} />
        )}
        {linha.gestoes.governador && (
          <FaixasGestao d={d} gestoes={linha.gestoes.governador} cargo="Governador" selecionada={sel?.chave} aoEscolher={escolher("Governador")} foco={foco} />
        )}
        {ativas.map((s) => (
          <div key={s.id} className="border-t border-border pt-2">
            <p className="text-sm font-semibold">
              {s.rotulo} <span className="font-normal text-muted-foreground">({s.unidade})</span>
            </p>
            <p className="text-xs text-muted-foreground">{resumoSerie(s, d)}</p>
            <LinhaSerie
              d={d}
              s={s}
              cor={corDoTema(s.tema)}
              faixa={sel ? { de: sel.g.inicio, ate: sel.g.fim } : null}
              foco={foco}
              aoFocar={setFoco}
              nomeEstado={nomeEstado}
              nomeLugar={lugar}
              reserva={reserva}
            />
          </div>
        ))}
        <EixoAnos d={d} foco={foco} reserva={reserva} />
      </div>
      <div className="sticky bottom-2 z-10">
        <PainelAno ano={foco} series={ativas} gestoes={linha.gestoes} nomeEstado={nomeEstado} />
      </div>

      <div ref={resumoRef} aria-live="polite" className="scroll-mb-24">
        {sel ? (
          <div className="border border-t-4 border-border bg-card p-3" style={{ borderTopColor: "var(--bronze)" }}>
            <p className="text-xs font-semibold tracking-wider uppercase text-bronze-texto">
              {sel.cargo}: {nomeCurto(sel.g)}, {sel.g.inicio} a {sel.g.fim}
            </p>
            <ul className="mt-2 flex flex-col gap-1 text-sm">
              {ativas.map((s) => {
                const cf = comecoEFim(s, sel.g);
                return (
                  <li key={s.id}>
                    {s.rotulo}:{" "}
                    {cf
                      ? `${formatarValor(s, cf[0].valor)} em ${cf[0].ano}, ${formatarValor(s, cf[1].valor)} em ${cf[1].ano}`
                      : "sem dois anos com dado neste período"}
                    {s.responsavel !== "—" && <span className="text-muted-foreground"> · responde: {s.responsavel}</span>}
                  </li>
                );
              })}
            </ul>
            <p className="mt-2 text-xs text-muted-foreground">
              Começo = último ano antes da posse, quando há. Os números mostram o que aconteceu no período, não o que a
              gestão causou: muita coisa depende de outros governos e da economia.
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Toque no nome de um prefeito ou governador para ver cada número no começo e no fim do período.
          </p>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Fontes: {[...new Set(linha.series.map((s) => s.fonte_nome))].join("; ")}; TSE (eleitos); IBGE (IPCA). Faltam
        anos onde a fonte não publica ou ainda não foi carregada. Pontos só onde há dado de {lugar}.
      </p>
    </div>
  );
}
