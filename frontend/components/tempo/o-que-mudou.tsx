"use client";

/**
 * "O que mudou" (protótipo B): frases literais tiradas das séries do lugar; tocar numa abre a
 * pergunta completa, com a série, quem governava em cada período e os números ligados (o gasto da
 * área, a taxa ao lado do estado e do Brasil). As faixas só situam no tempo: não mostram causa.
 */
import { useEffect, useState } from "react";

import { corDoTema, dominioDe } from "@/components/tempo/ao-longo-do-tempo";
import { EixoAnos, FaixasGestao, LinhaSerie, PainelAno, resumoSerie, useAnoFoco } from "@/components/tempo/eixo-tempo";
import type { TempoDoLugar, SerieTempo } from "@/lib/api";
import { type Descoberta, formatarValor, gerarDescobertas } from "@/lib/descobertas";

/** O que mostrar junto de cada série na pergunta completa. */
const LIGADAS: Record<string, string[]> = {
  homicidios: ["gasto_seguranca_estado", "gasto_seguranca_prefeitura"],
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

function ultimoComparado(s: SerieTempo, nomeEstado: string, lugar: string) {
  const fim = s.pontos[s.pontos.length - 1];
  if (!fim || s.comparacoes.length === 0) return null;
  const partes = s.comparacoes
    .map((c) => {
      const p = c.pontos.find((x) => x.ano === fim.ano);
      return p ? `${c.rotulo === "estado" ? nomeEstado : c.rotulo} ${formatarValor(s, p.valor)}` : null;
    })
    .filter(Boolean);
  return partes.length ? `${s.rotulo} em ${fim.ano}: ${lugar} ${formatarValor(s, fim.valor)}; ${partes.join("; ")}.` : null;
}

export function OQueMudou({ linha, lugar, nomeEstado }: { linha: TempoDoLugar; lugar: string; nomeEstado: string }) {
  const descobertas = gerarDescobertas(linha, lugar, nomeEstado);
  const [aberta, setAberta] = useState<string | null>(null);
  const [todas, setTodas] = useState(false);
  // Ao abrir, a resposta aparece logo abaixo do cartão tocado e a tela vai até ela (o título recebe
  // o foco, para quem usa leitor de tela ou teclado).
  useEffect(() => {
    if (!aberta) return;
    const el = document.getElementById(`pergunta-${aberta}`);
    if (!el) return;
    const reduzido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "start" });
    el.querySelector<HTMLElement>("h3")?.focus({ preventScroll: true });
  }, [aberta]);
  if (descobertas.length === 0) return null;
  const porId = new Map(linha.series.map((s) => [s.id, s]));
  const atual = descobertas.find((x) => x.serie === aberta) ?? null;

  return (
    <section aria-labelledby="o-que-mudou" className="flex flex-col gap-3">
      <h2 id="o-que-mudou" className="text-xl">
        O que mudou em {lugar}
      </h2>
      {/* dense: com a resposta aberta ocupando a linha toda, os outros cartões não deixam buraco. */}
      <ul className="grid grid-flow-row-dense gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
        {descobertas.map((x, i) => [
          <li key={x.serie} className={i >= 3 && !todas && aberta !== x.serie ? "hidden sm:flex" : "flex"}>
            <button
              type="button"
              aria-expanded={aberta === x.serie}
              aria-controls={`pergunta-${x.serie}`}
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
          </li>,
          aberta === x.serie && atual ? (
            <li key={`${x.serie}-resposta`} id={`pergunta-${x.serie}`} className="col-span-full scroll-mt-24" aria-live="polite">
              <Pergunta d={atual} linha={linha} porId={porId} nomeEstado={nomeEstado} lugar={lugar} />
            </li>
          ) : null,
        ])}
      </ul>
      {descobertas.length > 3 && !todas && (
        <button type="button" onClick={() => setTodas(true)} className="botao-linha self-start sm:hidden">
          Mais descobertas ({descobertas.length - 3})
        </button>
      )}
    </section>
  );
}

function Pergunta({
  d: x,
  linha,
  porId,
  nomeEstado,
  lugar,
}: {
  d: Descoberta;
  linha: TempoDoLugar;
  porId: Map<string, SerieTempo>;
  lugar: string;
  nomeEstado: string;
}) {
  const s = porId.get(x.serie)!;
  const dom = dominioDe(linha);
  const [foco, setFoco] = useAnoFoco();
  // Cruzamento só com dado suficiente: ao menos 4 anos em comum com a série principal.
  const anosPrincipal = new Set(s.pontos.map((p) => p.ano));
  const candidatas = (LIGADAS[x.serie] ?? []).map((id) => porId.get(id)).filter((v): v is SerieTempo => Boolean(v));
  const emComum = (l: SerieTempo) => l.pontos.filter((p) => anosPrincipal.has(p.ano)).length;
  const suficientes = candidatas.filter((l) => emComum(l) >= 4);
  const ligadas = suficientes.slice(0, 1);
  const poucas = candidatas.filter((l) => emComum(l) < 4);
  const taxa = x.serie === "homicidios" ? porId.get("homicidios_taxa") : undefined;
  const cargos = s.responsavel === "estado" ? ["governador"] : s.responsavel === "prefeitura" ? ["prefeito"] : ["prefeito", "governador"];
  const curta = s.decimais <= 1 && !s.unidade.startsWith("R$");
  // Se alguma linha tem estado e Brasil, todas reservam a coluna da direita (anos alinhados).
  const reserva = [s, ...ligadas].some((v) => v.comparacoes.length > 0);
  return (
    <div className="flex flex-col gap-3 border border-t-4 border-border bg-card p-4" style={{ borderTopColor: corDoTema(x.tema) }}>
      <h3 tabIndex={-1} className="text-xl focus:outline-none">{x.pergunta}</h3>
      <div className="flex flex-col gap-1">
        {cargos.includes("prefeito") && linha.gestoes.prefeito && (
          <FaixasGestao d={dom} gestoes={linha.gestoes.prefeito} cargo="Prefeito" foco={foco} />
        )}
        {cargos.includes("governador") && linha.gestoes.governador && (
          <FaixasGestao d={dom} gestoes={linha.gestoes.governador} cargo="Governador" foco={foco} />
        )}
        <p className="pt-1 text-sm font-semibold">
          {s.rotulo} <span className="font-normal text-muted-foreground">({s.unidade})</span>
        </p>
        <p className="text-xs text-muted-foreground">{resumoSerie(s, dom)}</p>
        <LinhaSerie d={dom} s={s} cor={corDoTema(s.tema)} todos={curta} altura={110} foco={foco} aoFocar={setFoco} nomeEstado={nomeEstado} nomeLugar={lugar} reserva={reserva} />
        {ligadas.map((l) => (
          <div key={l.id} className="border-t border-border pt-2">
            <p className="text-sm font-semibold">
              {l.rotulo} <span className="font-normal text-muted-foreground">({l.unidade})</span>
            </p>
            <p className="text-xs text-muted-foreground">{resumoSerie(l, dom)}</p>
            <LinhaSerie d={dom} s={l} cor={corDoTema(l.tema)} foco={foco} aoFocar={setFoco} nomeEstado={nomeEstado} nomeLugar={lugar} reserva={reserva} />
          </div>
        ))}
        <EixoAnos d={dom} foco={foco} reserva={reserva} />
      </div>
      <PainelAno ano={foco} series={[s, ...ligadas]} gestoes={linha.gestoes} nomeEstado={nomeEstado} />
      {taxa && ultimoComparado(taxa, nomeEstado, lugar) && (
        <p className="text-sm">{ultimoComparado(taxa, nomeEstado, lugar)}</p>
      )}
      {!taxa && ultimoComparado(s, nomeEstado, lugar) && <p className="text-sm">{ultimoComparado(s, nomeEstado, lugar)}</p>}
      {poucas.map((l) => (
        <p key={l.id} className="text-sm text-muted-foreground">
          {l.rotulo}: só há dados de {l.pontos[0]?.ano} a {l.pontos[l.pontos.length - 1]?.ano}; poucos anos em comum para
          comparar.
        </p>
      ))}
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
