"use client";

import { useEffect, useState } from "react";

import {
  Bloco,
  Fagulha,
  GraficoDeLinha,
  Linha,
  Seg,
  Tabela,
  Vazio,
  num,
} from "@/components/painel-acessos-partes";
import { formatarData } from "@/lib/formato";
import {
  COR_DA_FAIXA,
  GRADE_UFS,
  type ModoDePaginas,
  NOMES_UF,
  ORIGENS,
  PERIODOS,
  RECURSOS,
  type Resumo,
  SECOES,
  baseDeComparacao,
  cargosPresentes,
  diaCurto,
  diaDeMaiorMedia,
  faixaDoMapa,
  filtrarRepresentantes,
  formatarPercentual,
  nomeDaPagina,
  ordenarPaginas,
  percentual,
  sinal,
  textoDaDiferenca,
} from "@/lib/painel-acessos";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto";

type Aba = "pag" | "rep" | "reg" | "uso";
type Aparelho = "todos" | "celular" | "computador";
type Item = { param: string; rotulo: string };

export function PainelDados({ token, sair }: { token: string; sair: () => void }) {
  const [periodo, setPeriodo] = useState<number>(7);
  const [aparelho, setAparelho] = useState<Aparelho>("todos");
  const [origem, setOrigem] = useState<string | null>(null);
  const [uf, setUf] = useState<string | null>(null);
  const [item, setItem] = useState<Item | null>(null);
  const [aba, setAba] = useState<Aba>("pag");
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [erro, setErro] = useState("");
  const [chaveCarregada, setChaveCarregada] = useState("");

  const consulta = new URLSearchParams({ dias: String(periodo) });
  if (aparelho !== "todos") consulta.set("aparelho", aparelho);
  if (origem) consulta.set("origem", origem);
  if (uf) consulta.set("uf", uf);
  if (item) consulta.set("item", item.param);
  const chave = consulta.toString();
  // Enquanto a resposta mostrada não é a da consulta atual, os números estão sendo atualizados.
  const atualizando = chaveCarregada !== chave;

  useEffect(() => {
    const ctl = new AbortController();
    fetch(`${API}/painel/resumo?${chave}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: ctl.signal,
    })
      .then(async (r) => {
        if (r.status === 401) return sair();
        if (!r.ok) return setErro("Não deu para carregar os números agora.");
        setResumo(await r.json());
        setChaveCarregada(chave);
        setErro("");
      })
      .catch((e) => {
        if (e?.name !== "AbortError") setErro("Não deu para falar com o servidor.");
      });
    return () => ctl.abort();
  }, [chave, token, sair]);

  const aoEscolherItem = (param: string, rotulo: string) =>
    setItem((atual) => (atual?.param === param ? null : { param, rotulo }));
  const irPara = (a: Aba) => {
    setAba(a);
    document.getElementById("p-detalhes")?.scrollIntoView();
  };

  return (
    <>
      <div className="flex flex-col gap-3 border-y border-border py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            <Seg rotulo="Período" opcoes={PERIODOS} valor={periodo} aoMudar={setPeriodo} />
            <Seg
              rotulo="Aparelho"
              opcoes={[
                { v: "todos", n: "Todos" },
                { v: "celular", n: "Celular" },
                { v: "computador", n: "Computador" },
              ]}
              valor={aparelho}
              aoMudar={setAparelho}
            />
          </div>
          <button type="button" onClick={sair} className="botao-linha">
            Sair
          </button>
        </div>
        <p className="text-xs leading-snug text-muted-foreground">
          Período e aparelho valem para tudo. Origem (toque numa barra de &ldquo;De onde vieram&rdquo;) também.
          Estado vale só para a lista de cidades. Tocar numa página, num representante ou num partido mostra a
          série dele e não filtra o resto.
        </p>
        {(origem || uf || item) && (
          <ul className="flex flex-wrap gap-2 text-sm">
            {origem && (
              <Chip texto={`Só visitas vindas de ${ORIGENS[origem]?.toLowerCase() ?? origem}`} aoLimpar={() => setOrigem(null)} />
            )}
            {uf && <Chip texto={`Cidades de ${NOMES_UF[uf] ?? uf}`} aoLimpar={() => setUf(null)} />}
            {item && <Chip texto={`Série de ${item.rotulo}`} aoLimpar={() => setItem(null)} />}
          </ul>
        )}
      </div>
      <p role="status" className="sr-only">
        {atualizando ? "Atualizando os números." : resumo ? "Números atualizados." : ""}
      </p>
      {erro && <p className="text-sm font-medium">{erro}</p>}
      {!resumo && !erro && <p className="text-muted-foreground">Carregando...</p>}
      {resumo && (
        <div className={`flex flex-col gap-8 ${atualizando ? "opacity-70" : ""}`} aria-busy={atualizando}>
          <Numeros r={resumo} dias={periodo} />
          <Destaques r={resumo} escolher={aoEscolherItem} irPara={irPara} />
          <div className="grid gap-8 lg:grid-cols-[3fr_2fr] lg:gap-x-10">
            <Tempo r={resumo} rotuloDoItem={item?.rotulo ?? null} />
            <Origens r={resumo} origem={origem} aoEscolher={(o) => setOrigem((a) => (a === o ? null : o))} />
          </div>
          <section aria-labelledby="p-detalhes" id="p-detalhes" className="flex flex-col gap-4 border-t border-foreground pt-3">
            <h2 id="p-detalhes-t" className="sr-only">
              Detalhes
            </h2>
            <Seg
              rotulo="Escolher detalhe"
              opcoes={[
                { v: "pag", n: "Páginas" },
                { v: "rep", n: "Representantes" },
                { v: "reg", n: "Regiões" },
                { v: "uso", n: "Uso do site" },
              ]}
              valor={aba}
              aoMudar={setAba}
            />
            {aba === "pag" && <AbaPaginas r={resumo} dias={periodo} item={item} escolher={aoEscolherItem} />}
            {aba === "rep" && <AbaRepresentantes r={resumo} dias={periodo} item={item} escolher={aoEscolherItem} />}
            {aba === "reg" && <AbaRegioes r={resumo} uf={uf} aoEscolherUf={(u) => setUf((a) => (a === u ? null : u))} />}
            {aba === "uso" && <AbaUso r={resumo} />}
          </section>
          <Limites r={resumo} />
        </div>
      )}
    </>
  );
}

function Chip({ texto, aoLimpar }: { texto: string; aoLimpar: () => void }) {
  return (
    <li className="flex items-center gap-2">
      <span>{texto}</span>
      <button type="button" onClick={aoLimpar} className={`min-h-11 rounded-sm border border-muted-foreground/60 px-3 text-sm ${FOCO}`}>
        Limpar
      </button>
    </li>
  );
}

function Numeros({ r, dias }: { r: Resumo; dias: number }) {
  const base = baseDeComparacao(dias);
  const itens = [
    { nome: "Visitas", par: r.tiles.visitas, vals: r.serie.map((p) => p.visitas) },
    { nome: "Páginas vistas", par: r.tiles.paginas_vistas, vals: r.serie.map((p) => p.paginas_vistas) },
    { nome: "Buscas por CEP", par: r.tiles.buscas_cep, vals: r.serie.map((p) => p.buscas_cep) },
    { nome: "Compartilhamentos", par: r.tiles.compartilhamentos, vals: r.serie.map((p) => p.compartilhamentos) },
  ];
  return (
    <section aria-labelledby="p-numeros">
      <h2 id="p-numeros" className="sr-only">
        Números do período
      </h2>
      <ul className="grid grid-cols-2 lg:grid-cols-4">
        {itens.map((t, i) => (
          <li key={t.nome} className={`min-w-0 border-b border-border py-2.5 ${i % 2 ? "border-l pl-3 lg:pl-3" : "pr-3"} lg:border-l lg:px-3 lg:first:border-l-0 lg:first:pl-0`}>
            <p className="text-sm text-muted-foreground">{t.nome}</p>
            <p className="text-3xl font-semibold tabular-nums">{num(t.par.atual)}</p>
            <Fagulha valores={t.vals} />
            <p className="text-xs tabular-nums">{textoDaDiferenca(t.par.atual, t.par.anterior, base)}</p>
          </li>
        ))}
      </ul>
      {dias === 1 && (
        <p className="mt-1 text-xs text-muted-foreground">
          Hoje ainda está em contagem; a comparação é com o dia de ontem inteiro. O site não grava hora.
        </p>
      )}
    </section>
  );
}

function Destaques({
  r,
  escolher,
  irPara,
}: {
  r: Resumo;
  escolher: (param: string, rotulo: string) => void;
  irPara: (a: Aba) => void;
}) {
  const mais = ordenarPaginas("mais", r.paginas, r.rotas_fixas)[0];
  const alta = ordenarPaginas("alta", r.paginas, r.rotas_fixas)[0];
  const menos = ordenarPaginas("menos", r.paginas, r.rotas_fixas)[0];
  const rep = [...r.representantes].sort((a, b) => b.atual - a.atual)[0];
  const ufTop = r.ufs[0];
  const cidade = r.cidades.itens[0];
  const cartoes = [
    {
      k: "mais",
      rotulo: "Página mais vista",
      nome: mais ? nomeDaPagina(mais.chave) : "sem visita",
      q: mais ? `${num(mais.atual)} vistas` : "",
      aoClicar: mais && (() => { escolher(`pagina:${mais.chave}`, nomeDaPagina(mais.chave)); irPara("pag"); }),
    },
    {
      k: "alta",
      rotulo: "Página em alta",
      nome: alta ? nomeDaPagina(alta.chave) : "nenhuma subiu",
      q: alta ? `+${num(alta.dif)} ${baseDeComparacao(r.dias)}` : "",
      aoClicar: alta && (() => { escolher(`pagina:${alta.chave}`, nomeDaPagina(alta.chave)); irPara("pag"); }),
    },
    {
      k: "menos",
      rotulo: "Página de conteúdo menos vista",
      nome: menos ? nomeDaPagina(menos.chave) : "sem visita",
      q: menos ? `${num(menos.atual)} ${menos.atual === 1 ? "vista" : "vistas"}` : "",
      aoClicar: menos && (() => { escolher(`pagina:${menos.chave}`, nomeDaPagina(menos.chave)); irPara("pag"); }),
    },
    {
      k: "rep",
      rotulo: "Representante mais procurado",
      nome: rep ? rep.nome : "nenhum",
      q: rep ? `${num(rep.atual)} aberturas` : "",
      aoClicar: rep && (() => irPara("rep")),
    },
    {
      k: "uf",
      rotulo: "Estado com mais buscas",
      nome: ufTop ? (NOMES_UF[ufTop.uf] ?? ufTop.uf) : "sem dado",
      q: ufTop ? `${num(ufTop.total)} buscas` : "",
      aoClicar: ufTop && (() => irPara("reg")),
    },
    {
      k: "cid",
      rotulo: "Cidade mais buscada",
      nome: cidade ? `${cidade.nome}-${cidade.uf}` : `nenhuma com ${r.cidades.minimo} buscas`,
      q: cidade ? `${num(cidade.total)} buscas` : "",
      aoClicar: cidade && (() => irPara("reg")),
    },
  ];
  return (
    <section aria-labelledby="p-destaques">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="p-destaques" className="text-base font-semibold">
          Destaques do período
        </h2>
        <span className="text-xs text-muted-foreground">Toque para ver o detalhe</span>
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-1.5 lg:grid-cols-6">
        {cartoes.map((c) => {
          const miolo = (
            <>
              <span className="text-xs leading-tight text-muted-foreground">{c.rotulo}</span>
              <span className="text-[15px] leading-tight font-semibold [overflow-wrap:anywhere]">{c.nome}</span>
              <span className="mt-auto text-xs tabular-nums">{c.q}</span>
            </>
          );
          const classe = "flex min-h-28 w-full min-w-0 flex-col gap-0.5 rounded border border-border bg-card px-2.5 py-2 text-left";
          return (
            <li key={c.k} className="flex min-w-0">
              {c.aoClicar ? (
                <button type="button" onClick={c.aoClicar} className={`${classe} ${FOCO}`}>
                  {miolo}
                </button>
              ) : (
                <div className={classe}>{miolo}</div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Tempo({ r, rotuloDoItem }: { r: Resumo; rotuloDoItem: string | null }) {
  const [forma, setForma] = useState<"vis" | "pag" | "duas">("vis");
  const series = [
    forma !== "pag" && { nome: "Visitas", valores: r.serie.map((p) => p.visitas), cor: "var(--chart-1)" },
    forma !== "vis" && { nome: "Páginas vistas", valores: r.serie.map((p) => p.paginas_vistas), cor: "var(--chart-5)" },
  ].filter((s): s is { nome: string; valores: number[]; cor: string } => !!s);
  const nomeItem = rotuloDoItem ?? r.item?.rotulo ?? "";
  return (
    <Bloco id="p-tempo" titulo="Visitas ao longo do tempo">
      <Seg
        rotulo="Mostrar no gráfico"
        opcoes={[
          { v: "vis", n: "Visitas" },
          { v: "pag", n: "Páginas vistas" },
          { v: "duas", n: "As duas" },
        ]}
        valor={forma}
        aoMudar={setForma}
      />
      <GraficoDeLinha nome="Visitas e páginas vistas por dia" dias={r.serie} series={series} />
      {r.dias === 1 && <p className="text-xs text-muted-foreground">O último ponto é hoje, ainda em contagem.</p>}
      <Tabela
        titulo="Visitas e páginas vistas por dia"
        colunas={["Dia", "Visitas", "Páginas vistas"]}
        linhas={r.serie.map((p) => [`${diaCurto(p.dia)}, ${p.semana}`, p.visitas, p.paginas_vistas])}
      />
      {r.item && (
        <div className="mt-6 border-l-2 border-bronze pl-3">
          <h3 className="text-sm font-semibold">Só &ldquo;{nomeItem}&rdquo;</h3>
          <p className="text-xs text-muted-foreground">
            {num(r.item.atual)} no período, {textoDaDiferenca(r.item.atual, r.item.anterior, baseDeComparacao(r.dias))}. O resto do
            painel não muda.
          </p>
          <GraficoDeLinha
            nome={`Série de ${nomeItem}`}
            dias={r.item.serie}
            series={[{ nome: "Vistas", valores: r.item.serie.map((s) => s.total), cor: "var(--bronze)" }]}
          />
          <Tabela titulo={`Série de ${nomeItem}`} colunas={["Dia", "Vistas"]} linhas={r.item.serie.map((s) => [diaCurto(s.dia), s.total])} />
        </div>
      )}
      <Fonte />
    </Bloco>
  );
}

function Origens({ r, origem, aoEscolher }: { r: Resumo; origem: string | null; aoEscolher: (o: string) => void }) {
  const total = r.origens.reduce((s, o) => s + o.atual, 0);
  const maior = r.origens[0]?.atual ?? 0;
  return (
    <Bloco id="p-origem" titulo="De onde vieram" nota="Toque numa origem para filtrar todo o painel. Vale o aparelho escolhido.">
      {r.origens.length === 0 ? (
        <Vazio>Nenhuma visita neste período.</Vazio>
      ) : (
        r.origens.map((o) => (
          <Linha
            key={o.chave}
            nome={ORIGENS[o.chave] ?? o.chave}
            valor={`${num(o.atual)} · ${formatarPercentual(percentual(o.atual, total))}`}
            pct={percentual(o.atual, maior)}
            ativo={origem === o.chave}
            aoClicar={() => aoEscolher(o.chave)}
          />
        ))
      )}
      <Fonte />
    </Bloco>
  );
}

function AbaPaginas({ r, dias, item, escolher }: { r: Resumo; dias: number; item: Item | null; escolher: (p: string, rot: string) => void }) {
  const [modo, setModo] = useState<ModoDePaginas>("mais");
  const [tudo, setTudo] = useState(false);
  const [busca, setBusca] = useState("");
  const lista = ordenarPaginas(modo, r.paginas, r.rotas_fixas, busca);
  const visiveis = tudo ? lista : lista.slice(0, 8);
  const maior = Math.max(1, ...lista.map((p) => (modo === "alta" ? p.dif : p.atual)));
  const base = baseDeComparacao(dias).replace("que ", "");
  return (
    <Bloco id="p-paginas" titulo="Páginas do site" nota="Tocar numa página mostra só a série dela; as outras listas não mudam. Perfis individuais ficam em Representantes.">
      <Seg
        rotulo="Ordenar páginas"
        opcoes={[
          { v: "mais", n: "Mais vistas" },
          { v: "menos", n: "Menos vistas" },
          { v: "alta", n: "Em alta" },
          { v: "zero", n: "Sem visita" },
        ] as const}
        valor={modo}
        aoMudar={(m) => {
          setModo(m);
          setTudo(false);
        }}
      />
      {modo === "menos" && <p className="mt-1 text-xs text-muted-foreground">Só páginas de conteúdo; ficam de fora a inicial, privacidade, acessibilidade, status, avisos e apoio.</p>}
      {modo === "zero" && <p className="mt-1 text-xs text-muted-foreground">Páginas de conteúdo sem nenhuma vista no período, com o que tinham antes.</p>}
      <div className="my-2">
        <label htmlFor="p-busca-pag" className="mb-1 block text-xs text-muted-foreground">
          Buscar página
        </label>
        <input
          id="p-busca-pag"
          type="search"
          value={busca}
          autoComplete="off"
          onChange={(e) => setBusca(e.target.value)}
          className="h-11 w-full rounded-sm border border-muted-foreground/60 bg-card px-2.5 text-base"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {lista.length} {lista.length === 1 ? "página" : "páginas"}. Número: vistas · diferença em relação a {base}.
      </p>
      {lista.length === 0 ? (
        <Vazio>Nenhuma página neste recorte.</Vazio>
      ) : (
        visiveis.map((p) => (
          <Linha
            key={p.chave}
            nome={nomeDaPagina(p.chave)}
            detalhe={nomeDaPagina(p.chave) === p.chave ? undefined : p.chave}
            valor={modo === "zero" ? `0 · ${num(p.anterior)} antes` : modo === "alta" ? `${sinal(p.dif)} · ${num(p.atual)}` : `${num(p.atual)} · ${sinal(p.dif)}`}
            pct={modo === "zero" ? 0 : percentual(modo === "alta" ? p.dif : p.atual, maior)}
            ativo={item?.param === `pagina:${p.chave}`}
            aoClicar={modo === "zero" ? undefined : () => escolher(`pagina:${p.chave}`, nomeDaPagina(p.chave))}
          />
        ))
      )}
      {lista.length > 8 && (
        <button type="button" onClick={() => setTudo(!tudo)} className={`min-h-11 text-sm text-bronze-texto underline underline-offset-4 ${FOCO}`}>
          {tudo ? "Mostrar só 8" : `Ver as ${lista.length} páginas`}
        </button>
      )}
      <Tabela
        titulo="Páginas do site no período"
        colunas={["Página", "Vistas", "Antes"]}
        linhas={r.paginas.map((p) => [`${nomeDaPagina(p.chave)} (${p.chave})`, p.atual, p.anterior])}
      />
      <Fonte />
    </Bloco>
  );
}

function AbaRepresentantes({ r, dias, item, escolher }: { r: Resumo; dias: number; item: Item | null; escolher: (p: string, rot: string) => void }) {
  const [cargo, setCargo] = useState("todos");
  const [uf, setUf] = useState("todas");
  const cargos = cargosPresentes(r.representantes);
  const lista = filtrarRepresentantes(r.representantes, cargo, uf);
  const maior = lista[0]?.atual ?? 1;
  const ufsPresentes = [...new Set(r.representantes.map((x) => x.uf).filter((u): u is string => !!u))].sort();
  const partidoMax = r.partidos[0]?.atual ?? 1;
  return (
    <div className="flex flex-col gap-8">
      <Bloco id="p-reps" titulo="Representantes mais procurados">
        <p className="my-1 border-l-2 border-foreground pl-2.5 text-sm">
          Ranking só nesta área privada. O site público não ordena políticos.
        </p>
        <p className="text-xs text-muted-foreground">
          Nome, cargo e estado vêm do banco do Panóptico; só aparecem perfis que existem nele. Os filtros de cargo e
          estado valem para esta lista (entre os {num(r.representantes.length)} perfis mais abertos).
        </p>
        <div className="mt-2">
          <span className="mb-1 block text-xs text-muted-foreground">Cargo</span>
          <Seg rotulo="Cargo" opcoes={[{ v: "todos", n: "Todos" }, ...cargos.map((c) => ({ v: c, n: c }))]} valor={cargo} aoMudar={setCargo} />
        </div>
        <div className="my-2">
          <label htmlFor="p-uf-rep" className="mb-1 block text-xs text-muted-foreground">
            Estado do representante
          </label>
          <select
            id="p-uf-rep"
            value={uf}
            onChange={(e) => setUf(e.target.value)}
            className="h-11 w-full rounded-sm border border-muted-foreground/60 bg-card px-2 text-base"
          >
            <option value="todas">Todos os estados</option>
            {ufsPresentes.map((u) => (
              <option key={u} value={u}>
                {NOMES_UF[u] ?? u}
              </option>
            ))}
          </select>
        </div>
        <p className="text-xs text-muted-foreground">
          {lista.length} com abertura de perfil. Número: aberturas · diferença em relação a {baseDeComparacao(dias).replace("que ", "")}.
        </p>
        {lista.length === 0 ? (
          <Vazio>Nenhuma abertura de perfil neste recorte.</Vazio>
        ) : (
          lista.slice(0, 8).map((x) => (
            <Linha
              key={x.chave}
              nome={x.nome}
              detalhe={`${x.cargo}${x.uf ? `, ${x.uf}` : ""}${x.partido ? `, ${x.partido}` : ""}`}
              valor={`${num(x.atual)} · ${sinal(x.atual - x.anterior)}`}
              pct={percentual(x.atual, maior)}
              ativo={item?.param === `perfil:${x.chave}`}
              aoClicar={() => escolher(`perfil:${x.chave}`, x.nome)}
            />
          ))
        )}
        <Tabela
          titulo="Representantes por aberturas de perfil"
          colunas={["Nome", "Cargo", "Estado", "Aberturas", "Antes"]}
          linhas={lista.map((x) => [x.nome, x.cargo, x.uf ?? "", x.atual, x.anterior])}
        />
        <Fonte />
      </Bloco>
      <Bloco id="p-projetos" titulo="Projetos mais abertos" nota="Só projetos que existem no banco; o nome é a sigla, o número e o ano.">
        {r.projetos.length === 0 ? (
          <Vazio>Nenhum projeto aberto neste período.</Vazio>
        ) : (
          r.projetos.slice(0, 6).map((p) => (
            <Linha key={p.chave} nome={p.rotulo} detalhe={p.casa} valor={`${num(p.atual)} · ${sinal(p.atual - p.anterior)}`} pct={percentual(p.atual, r.projetos[0].atual)} />
          ))
        )}
        <Fonte />
      </Bloco>
      <Bloco id="p-partidos" titulo="Partidos mais vistos" nota="Contam as aberturas da página de cada partido.">
        {r.partidos.length === 0 ? (
          <Vazio>Nenhuma página de partido aberta neste período.</Vazio>
        ) : (
          r.partidos.map((p) => (
            <Linha
              key={p.chave}
              nome={p.chave}
              valor={`${num(p.atual)} · ${sinal(p.atual - p.anterior)}`}
              pct={percentual(p.atual, partidoMax)}
              ativo={item?.param === `partido:${p.chave.toLowerCase()}`}
              aoClicar={() => escolher(`partido:${p.chave.toLowerCase()}`, p.chave)}
            />
          ))
        )}
        <Fonte />
      </Bloco>
    </div>
  );
}

function AbaRegioes({ r, uf, aoEscolherUf }: { r: Resumo; uf: string | null; aoEscolherUf: (u: string) => void }) {
  const totalUf = r.ufs.reduce((s, u) => s + u.total, 0);
  const porUf = new Map(r.ufs.map((u) => [u.uf, u.total]));
  const maior = r.ufs[0]?.total ?? 0;
  const maxRegiao = r.regioes[0]?.total ?? 0;
  return (
    <div className="flex flex-col gap-8">
      <Bloco
        id="p-regioes"
        titulo="Buscas por estado"
        nota={`Conta o estado que o resultado da busca devolveu (por CEP, cidade ou localização): ${num(totalUf)} buscas com resultado neste recorte. O site nunca guarda o CEP, e quem não buscou não entra aqui.`}
      >
        <h3 className="mt-2 text-sm font-medium">Regiões do Brasil</h3>
        {r.regioes.length === 0 ? (
          <Vazio>Nenhuma busca com resultado neste período.</Vazio>
        ) : (
          r.regioes.map((g) => (
            <Linha key={g.chave} nome={g.chave} valor={`${num(g.total)} · ${formatarPercentual(percentual(g.total, totalUf))}`} pct={percentual(g.total, maxRegiao)} />
          ))
        )}
      </Bloco>
      <div className="grid gap-8 lg:grid-cols-[430px_1fr] lg:gap-x-8">
        <Bloco id="p-mapa" titulo="Mapa em grade dos estados" nota="Toque num estado para ver as cidades dele. Esse filtro vale só para a lista de cidades abaixo.">
          <div className="mt-2 grid max-w-[430px] grid-cols-6 gap-[3px]">
            {Object.entries(GRADE_UFS).map(([sigla, [x, y]]) => {
              const total = porUf.get(sigla) ?? 0;
              return (
                <button
                  key={sigla}
                  type="button"
                  aria-pressed={uf === sigla}
                  aria-label={`${NOMES_UF[sigla]}: ${num(total)} buscas`}
                  onClick={() => aoEscolherUf(sigla)}
                  style={{ gridColumn: x + 1, gridRow: y + 1 }}
                  className={`flex min-h-11 flex-col items-center justify-center rounded-sm text-[13px] leading-none font-semibold text-foreground aria-pressed:outline-2 aria-pressed:outline-offset-1 aria-pressed:outline-foreground ${COR_DA_FAIXA[faixaDoMapa(total, maior)]} ${FOCO}`}
                >
                  {sigla}
                  <span className="mt-0.5 text-[11px] font-normal tabular-nums">{num(total)}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>Mais escuro = mais buscas (em quartos do estado com mais buscas).</span>
          </p>
        </Bloco>
        <Bloco id="p-ufs" titulo="Estados com mais buscas">
          {r.ufs.length === 0 ? (
            <Vazio>Nenhuma busca com resultado neste período.</Vazio>
          ) : (
            r.ufs.slice(0, 6).map((u) => (
              <Linha
                key={u.uf}
                nome={NOMES_UF[u.uf] ?? u.uf}
                valor={`${num(u.total)} · ${formatarPercentual(percentual(u.total, totalUf))}`}
                pct={percentual(u.total, maior)}
                ativo={uf === u.uf}
                aoClicar={() => aoEscolherUf(u.uf)}
              />
            ))
          )}
          <Tabela titulo="Buscas por estado" colunas={["Estado", "Buscas"]} linhas={r.ufs.map((u) => [NOMES_UF[u.uf] ?? u.uf, u.total])} />
        </Bloco>
      </div>
      <Bloco
        id="p-cidades"
        titulo={uf ? `Cidades mais buscadas em ${NOMES_UF[uf] ?? uf}` : "Cidades mais buscadas"}
        nota={`Cidade só aparece com ${r.cidades.minimo} buscas ou mais no período. Isso evita que uma cidade pequena exponha poucas pessoas.`}
      >
        {r.cidades.itens.length === 0 ? (
          <Vazio>Nenhuma cidade com {r.cidades.minimo} buscas ou mais neste recorte.</Vazio>
        ) : (
          r.cidades.itens.map((c) => <Linha key={c.ibge} nome={`${c.nome}-${c.uf}`} valor={num(c.total)} pct={percentual(c.total, r.cidades.itens[0].total)} />)
        )}
        {r.cidades.fora > 0 && (
          <p className="text-xs text-muted-foreground">
            {r.cidades.fora} {r.cidades.fora === 1 ? "cidade ficou" : "cidades ficaram"} de fora pela regra das {r.cidades.minimo} buscas.
          </p>
        )}
        <Fonte />
      </Bloco>
    </div>
  );
}

function Sec({ titulo, children, aberto }: { titulo: string; children: React.ReactNode; aberto?: boolean }) {
  return (
  <details open={aberto} className="group border-b border-border">
    <summary className={`flex min-h-12 cursor-pointer list-none items-center py-1.5 font-medium [&::-webkit-details-marker]:hidden ${FOCO}`}>
      <span aria-hidden className="w-4 text-bronze-texto group-open:hidden">+</span>
      <span aria-hidden className="hidden w-4 text-bronze-texto group-open:inline">−</span>
      {titulo}
    </summary>
    <div className="pb-3">{children}</div>
  </details>
);
}

function AbaUso({ r }: { r: Resumo }) {
  const { uso } = r;
  const maiorRec = Math.max(1, ...uso.recursos.map((x) => x.atual));
  const melhor = diaDeMaiorMedia(uso.dia_da_semana);
  const maiorDia = Math.max(1, ...uso.dia_da_semana.map((d) => d.media));
  const totalCep = uso.cep.com + uso.cep.sem;
  const lista = (itens: { chave: string; atual: number }[], rotulo: (c: string) => string) => {
    const m = Math.max(1, ...itens.map((x) => x.atual));
    return itens.length === 0 ? <Vazio>Nada contado neste período.</Vazio> : itens.map((x) => <Linha key={x.chave} nome={rotulo(x.chave)} valor={num(x.atual)} pct={percentual(x.atual, m)} />);
  };
  return (
    <div>
      <Sec titulo="Recursos usados" aberto>
        {uso.recursos.length === 0 ? <Vazio>Nenhum uso neste período.</Vazio> : uso.recursos.map((x) => <Linha key={x.chave} nome={RECURSOS[x.chave] ?? x.chave} valor={`${num(x.atual)} · ${sinal(x.atual - x.anterior)}`} pct={percentual(x.atual, maiorRec)} />)}
        <Fonte />
      </Sec>
      <Sec titulo="Busca por CEP: com e sem resultado">
        <p className="text-sm tabular-nums">
          <b>{num(uso.cep.com)}</b> com resultado e <b>{num(uso.cep.sem)}</b> sem resultado
          {totalCep > 0 && <> ({formatarPercentual(percentual(uso.cep.sem, totalCep))} sem resultado)</>}.
        </p>
        <p className="text-xs text-muted-foreground">Sem resultado é um CEP que os Correios não têm. O CEP em si nunca é guardado.</p>
        <Fonte />
      </Sec>
      <Sec titulo="Primeira e última página da visita">
        <h4 className="mt-1 text-sm font-medium">Entrada</h4>
        {lista(uso.entradas, nomeDaPagina)}
        <h4 className="mt-3 text-sm font-medium">Última página</h4>
        {lista(uso.ultimas, nomeDaPagina)}
        <p className="mt-1 text-xs text-muted-foreground">
          A última página só é contada quando a aba é fechada ou o visitante sai do site, e quem bloqueia scripts não entra.
        </p>
        <Fonte />
      </Sec>
      <Sec titulo="Seções do perfil abertas">
        <p className="text-xs text-muted-foreground">Conta quando alguém abre um bloco recolhido de uma seção ou toca num atalho do resumo do perfil.</p>
        {lista(uso.secoes, (c) => SECOES[c] ?? c)}
        <Fonte />
      </Sec>
      <Sec titulo="Dia da semana com mais visitas">
        {r.dias === 1 ? (
          <Vazio>Escolha 7 ou 30 dias para comparar os dias da semana.</Vazio>
        ) : (
          <>
            {melhor ? <p className="text-sm">Média por dia: {melhor.dia} tem {num(melhor.media)} visitas.</p> : <Vazio>Nenhuma visita neste período.</Vazio>}
            {uso.dia_da_semana
              .filter((d) => d.dias > 0)
              .map((d) => (
                <Linha key={d.dia} nome={d.dia} valor={`${num(d.media)} por dia`} pct={percentual(d.media, maiorDia)} detalhe={`${d.dias} ${d.dias === 1 ? "dia" : "dias"} no período`} />
              ))}
            <p className="mt-1 text-xs text-muted-foreground">Só o dia. O site não grava hora.</p>
          </>
        )}
        <Fonte />
      </Sec>
    </div>
  );
}

function Limites({ r }: { r: Resumo }) {
  return (
    <section aria-labelledby="p-limites" className="flex flex-col gap-2 text-sm text-muted-foreground">
      <h2 id="p-limites" className="text-lg font-semibold text-foreground">
        O que estes números são
      </h2>
      <p>
        {r.inicio_da_contagem
          ? `A contagem começou em ${formatarData(r.inicio_da_contagem)}. Nada antes disso foi medido.`
          : "A contagem ainda não registrou nenhum acesso."}{" "}
        Uma visita é uma sequência de páginas numa mesma aba do navegador. Ela não é uma pessoa: quem volta amanhã, ou abre numa aba nova,
        conta de novo. O dia é o de Brasília.
      </p>
      <p>
        Ficam de fora quem bloqueia scripts ou anúncios, quem pede para não ser rastreado, robôs e programas automáticos, e o aparelho de
        quem abre este painel. Por isso os números são um piso, não o total real.
      </p>
      <p>
        Nada identifica ninguém: sem IP, sem cookie, sem hora. O CEP digitado nunca é enviado; a busca só informa se teve resultado e, quando
        teve, o estado e a cidade que ela devolveu. Fora desta lista: termos de busca, hora do acesso, quem é novo ou volta, tempo de carga.
      </p>
      <p>Aparelho é o tipo de tela: celular e tablet (toque) ou computador (mouse).</p>
    </section>
  );
}

function Fonte() {
  return <p className="mt-2 text-xs text-muted-foreground">Fonte: contagem anônima do próprio site, em totais por dia.</p>;
}
