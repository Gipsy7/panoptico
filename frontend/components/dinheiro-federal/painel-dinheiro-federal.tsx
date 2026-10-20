"use client";

// Painel de dinheiro federal: mapa Brasil > estado > cidade, barra de ferramentas e painel
// lateral (folha de baixo no celular). O lugar e o ano vivem neste componente e a URL acompanha
// por history.pushState; assim a navegação é suave e o link continua compartilhável.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { MapaBrasil, type MapaControle } from "@/components/mapa/mapa-brasil";
import estilosMapa from "@/components/mapa/mapa-brasil.module.css";
import { Migalhas } from "@/components/ui/migalhas";
import type {
  DinheiroFederalCidade,
  DinheiroFederalEstado,
  DinheiroFederalMunicipio,
  DinheiroFederalPainel,
  DinheiroFederalUF,
} from "@/lib/api";
import { type ClasseMapa, type Lugar, type NivelMapa, classe, quantis } from "@/lib/mapa";

import { BuscaCidade } from "./busca-cidade";
import { estadoDoAno, municipioPorIbge, painelDoAno, semear } from "./cache";
import {
  Avisos,
  CabecalhoBrasil,
  CabecalhoCidade,
  CabecalhoEstado,
  CabecalhoPainel,
  CorpoBrasil,
  CorpoCidade,
  CorpoEstado,
  Fontes,
} from "./conteudo-painel";
import {
  ANO_PADRAO,
  type Indicador,
  NOME_INDICADOR,
  formatarIndicador,
  notaPopulacao,
  numero,
  porHab,
  reais,
  reaisA100,
  repHab,
  rotuloAno,
  valorIndicador,
} from "./formatos";
import { type LinhaLista, ListaLugares } from "./lista-lugares";
import estilos from "./painel-dinheiro-federal.module.css";
import { Secao } from "./pecas";

export type EstadoInicial = {
  uf: string | null;
  ibge: string | null;
  ano: number;
  painel: DinheiroFederalPainel;
  estado: DinheiroFederalEstado | null;
  municipio: DinheiroFederalMunicipio | null;
};

const INDICADORES = Object.keys(NOME_INDICADOR) as Indicador[];

function urlDe(uf: string | null, ibge: string | null, ano: number) {
  return `/impostos-e-repasses${uf ? `/${uf}` : ""}${uf && ibge ? `/${ibge}` : ""}${ano !== ANO_PADRAO ? `?ano=${ano}` : ""}`;
}

/** Lê /impostos-e-repasses/SC/4205407?ano=2024 da barra de endereço (botão voltar do navegador). */
function lerEndereco() {
  const partes = location.pathname.split("/").filter(Boolean).slice(1);
  const ano = Number(new URLSearchParams(location.search).get("ano"));
  return {
    uf: partes[0] ? partes[0].toUpperCase() : null,
    ibge: partes[0] && partes[1] ? partes[1] : null,
    ano: Number.isInteger(ano) && ano > 2000 ? ano : ANO_PADRAO,
  };
}

const valorCidade = (c: DinheiroFederalCidade | undefined) =>
  c && c.repasse != null && c.populacao ? c.repasse / c.populacao : null;

type Folha = "recolhida" | "meia" | "aberta";

export function PainelDinheiroFederal({ inicial }: { inicial: EstadoInicial }) {
  const [uf, setUf] = useState(inicial.uf);
  const [ibge, setIbge] = useState(inicial.ibge);
  const [ano, setAno] = useState(inicial.ano);
  const [ind, setInd] = useState<Indicador>("repHab");
  const [vista, setVista] = useState<"mapa" | "lista">("mapa");
  const [folha, setFolha] = useState<Folha>(inicial.ibge ? "meia" : "recolhida");
  const [buscaAberta, setBuscaAberta] = useState(false);
  const [painel, setPainel] = useState(inicial.painel);
  const [estado, setEstado] = useState(inicial.estado);
  const [municipio, setMunicipio] = useState(inicial.municipio);
  const [erro, setErro] = useState<string | null>(null);

  const raizRef = useRef<HTMLDivElement>(null);
  const topoFolhaRef = useRef<HTMLDivElement>(null);
  const folhaRef = useRef<HTMLElement>(null);
  const controle = useRef<MapaControle>(null);
  const buscaRef = useRef<HTMLDivElement>(null);

  // Veio outra renderização do servidor (ex.: botão voltar): acompanha o endereço novo.
  const chaveInicial = `${inicial.uf}|${inicial.ibge}|${inicial.ano}`;
  const [chaveVista, setChaveVista] = useState(chaveInicial);
  if (chaveVista !== chaveInicial) {
    setChaveVista(chaveInicial);
    setUf(inicial.uf);
    setIbge(inicial.ibge);
    setAno(inicial.ano);
    setFolha(inicial.ibge ? "meia" : "recolhida");
    setPainel(inicial.painel);
    setEstado(inicial.estado);
    setMunicipio(inicial.municipio);
  }

  useEffect(() => {
    semear(inicial.painel, inicial.estado, inicial.municipio);
  }, [inicial]);

  useEffect(() => {
    const aoVoltar = () => {
      const e = lerEndereco();
      setUf(e.uf);
      setIbge(e.ibge);
      setAno(e.ano);
      setFolha(e.ibge ? "meia" : "recolhida");
    };
    addEventListener("popstate", aoVoltar);
    return () => removeEventListener("popstate", aoVoltar);
  }, []);

  // Marca a página como "tela de app" (celular sem rolagem) enquanto ela está aberta. O atributo vive
  // só no <html>: com a página anterior escondida (Activity) a limpeza do efeito o retira.
  useEffect(() => {
    document.documentElement.dataset.appMapa = "1";
    return () => {
      delete document.documentElement.dataset.appMapa;
    };
  }, []);

  // ---- carga sob demanda (cache em memória) ----
  useEffect(() => {
    if (painel.ano === ano) return;
    let vivo = true;
    painelDoAno(ano).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setPainel(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [ano, painel.ano]);

  useEffect(() => {
    if (!uf || (estado?.uf === uf && estado.ano === ano)) return;
    let vivo = true;
    estadoDoAno(uf, ano).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setEstado(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [uf, ano, estado]);

  useEffect(() => {
    if (!ibge || municipio?.municipio.ibge === ibge) return;
    let vivo = true;
    municipioPorIbge(ibge).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setMunicipio(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [ibge, municipio]);

  // ---- navegação ----
  const navegar = useCallback(
    (lugar: Lugar) => {
      const novoUf = lugar.uf ?? null;
      const novoIbge = novoUf ? (lugar.municipio ?? null) : null;
      setUf(novoUf);
      setIbge(novoIbge);
      setFolha(novoIbge ? "meia" : "recolhida");
      setErro(null);
      history.pushState(null, "", urlDe(novoUf, novoIbge, ano));
    },
    [ano],
  );

  function trocarAno(novo: number) {
    setAno(novo);
    history.replaceState(null, "", urlDe(uf, ibge, novo));
  }

  // ---- dados derivados ----
  const anoMostrado = painel.ano;
  const ufLinha: DinheiroFederalUF | null = uf ? (painel.ufs.find((u) => u.uf === uf) ?? null) : null;
  const estadoOk = estado && estado.uf === uf && estado.ano === anoMostrado ? estado : null;
  const cidades = useMemo(() => estadoOk?.cidades ?? [], [estadoOk]);
  const porIbge = useMemo(() => new Map(cidades.map((c) => [c.ibge, c])), [cidades]);
  const mediaBrasil = repHab(painel.brasil);

  // Dentro do estado só existe repasse por habitante (a Receita não publica arrecadação por cidade).
  const cortesUf = useMemo(() => quantis(painel.ufs.map((u) => valorIndicador(u, ind))), [painel, ind]);
  const cortesMun = useMemo(() => quantis(cidades.map(valorCidade)), [cidades]);

  const classeMapa = (nivel: NivelMapa, id: string): ClasseMapa => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      return u ? classe(valorIndicador(u, ind), cortesUf) : 0;
    }
    return classe(valorCidade(porIbge.get(id)), cortesMun);
  };

  // Nomes das cidades no mapa: as mais populosas aparecem primeiro.
  const prioridadeMapa = (id: string) => porIbge.get(id)?.populacao;
  const rotuloMapa = (nivel: NivelMapa, id: string) => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      return u
        ? `${u.nome}: a União arrecadou ${reais(u.arrecadacao)} e repassou ${reais(u.repasse)} em ${anoMostrado}`
        : id;
    }
    const c = porIbge.get(id);
    return c ? `${c.nome}: a União repassou ${reais(c.repasse)} à prefeitura em ${anoMostrado}` : id;
  };

  const resumoMapa = (nivel: NivelMapa, id: string) => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      if (!u) return id;
      return (
        <div className="flex flex-col gap-0.5 text-sm">
          <strong>{u.nome}</strong>
          <span>Arrecadou {reais(u.arrecadacao)}</span>
          <span>Repassou {reais(u.repasse)}</span>
          <span>A cada R$ 100: {reaisA100(valorIndicador(u, "por100"))}</span>
          <span>Por habitante: {porHab(repHab(u))}</span>
          <span>Média do Brasil: {porHab(mediaBrasil)}</span>
        </div>
      );
    }
    const c = porIbge.get(id);
    if (!c) return id;
    return (
      <div className="flex flex-col gap-0.5 text-sm">
        <strong>{c.nome}</strong>
        <span>Repasse à prefeitura: {reais(c.repasse)}</span>
        <span>Por morador: {porHab(valorCidade(c))}</span>
        <span>Média do estado: {porHab(estadoOk?.media_estado_por_habitante)}</span>
        <span>Moradores: {numero(c.populacao)}</span>
      </div>
    );
  };

  // ---- legenda ----
  const nivelMun = Boolean(uf);
  const indEfetivo: Indicador = nivelMun ? "repHab" : ind;
  const valoresLegenda = (
    nivelMun ? cidades.map(valorCidade) : painel.ufs.map((u) => valorIndicador(u, indEfetivo))
  ).filter((v): v is number => v != null);
  const cortesLegenda = nivelMun ? cortesMun : cortesUf;
  const minimo = valoresLegenda.length ? Math.min(...valoresLegenda) : null;
  const maximo = valoresLegenda.length ? Math.max(...valoresLegenda) : null;
  const rotulosLegenda = [minimo, cortesLegenda[1] ?? null, cortesLegenda[3] ?? null, maximo]
    .map((v) => formatarIndicador(indEfetivo, v))
    .filter((t, i, todos) => i === 0 || t !== todos[i - 1]);
  const valorUnico = rotulosLegenda.length === 1;
  const cidadesComValor = cidades.filter((c) => valorCidade(c) != null);
  const nomeUnico = nivelMun && cidadesComValor.length === 1 ? cidadesComValor[0].nome : null;
  const unidadeLegenda = indEfetivo === "por100" ? "a cada R$ 100" : "por habitante";

  // ---- lista ----
  const linhas: LinhaLista[] = nivelMun
    ? cidades.map((c) => ({ id: c.ibge, nome: c.nome, c1: c.populacao, c2: c.repasse, c3: valorCidade(c), c4: null }))
    : painel.ufs.map((u) => ({
        id: u.uf,
        nome: u.nome,
        c1: u.arrecadacao,
        c2: u.repasse,
        c3: repHab(u),
        c4: valorIndicador(u, "por100"),
      }));

  // ---- painel ----
  const munOk = municipio && municipio.municipio.ibge === ibge ? municipio : null;
  const ufNome = ufLinha?.nome ?? uf ?? "";
  const nomeCidade = munOk?.municipio.nome ?? (ibge ? porIbge.get(ibge)?.nome : undefined) ?? "Cidade";
  const serieAno = munOk?.serie.find((s) => s.ano === anoMostrado);
  const notaPop = ufLinha ? notaPopulacao(ufLinha, anoMostrado) : "";
  const anos = painel.anos_disponiveis;
  const fontes = ibge && munOk ? munOk.fontes : (estadoOk?.fontes ?? painel.fontes);
  const carregando = painel.ano !== ano || (Boolean(uf) && !estadoOk) || (Boolean(ibge) && !munOk);
  const avisoAnoEmCurso = painel.avisos.filter((a) => a.startsWith("Ano em curso"));

  // Altura da parte sempre visível da folha (celular): alça + cabeçalho.
  const chaveCabecalho = `${uf}|${ibge}|${anoMostrado}|${Boolean(munOk)}`;
  useLayoutEffect(() => {
    const topo = topoFolhaRef.current;
    const raiz = raizRef.current;
    if (!topo || !raiz) return;
    const medir = () => raiz.style.setProperty("--espia", `${Math.min(topo.offsetHeight + 8, 320)}px`);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(topo);
    return () => ro.disconnect();
  }, [chaveCabecalho]);

  // ---- folha de baixo (celular): arrastar ----
  // Recolhida ou a meia altura, o conteúdo não rola e qualquer arraste vertical na folha a move.
  // Aberta, o conteúdo rola; puxar para baixo com ele no topo (ou pela alça) volta a fechar.
  // Durante o gesto a folha segue o dedo (translateY sem transição); ao soltar vai para a posição
  // mais próxima entre recolhida, meia altura e aberta (passou de 30% do vão já troca), ou para a
  // seguinte num gesto rápido.
  const arrasteFolha = useRef({
    ativo: false,
    y0: 0,
    base: 0,
    pos: 0,
    moveu: false,
    decidido: false,
    pelaAlca: false,
    amostras: [] as Array<[number, number]>,
    suprimirClique: false,
  });
  const folhaAtual = useRef(folha);
  useEffect(() => {
    folhaAtual.current = folha;
    // Fora do estado aberto o conteúdo não rola: volta ao topo.
    if (folha !== "aberta" && folhaRef.current) folhaRef.current.scrollTop = 0;
  }, [folha]);

  const alvosFolha = useCallback((): Record<Folha, number> => {
    const h = folhaRef.current?.offsetHeight ?? 0;
    const espia = Math.min((topoFolhaRef.current?.offsetHeight ?? 0) + 8, 320);
    const recolhida = Math.max(0, h - espia);
    const meia = Math.min(recolhida, Math.max(0, h - innerHeight * 0.55));
    return { recolhida, meia, aberta: 0 };
  }, []);

  const comecarArraste = useCallback((y: number, pelaAlca: boolean) => {
    const el = folhaRef.current;
    if (!el || !matchMedia("(max-width: 959px)").matches) return false;
    const t = getComputedStyle(el).transform;
    const base = t && t !== "none" ? new DOMMatrixReadOnly(t).m42 : 0;
    arrasteFolha.current = {
      ativo: true,
      y0: y,
      base,
      pos: base,
      moveu: false,
      decidido: false,
      pelaAlca,
      amostras: [[performance.now(), y]],
      suprimirClique: false,
    };
    return true;
  }, []);

  const moverArraste = useCallback(
    (y: number) => {
      const a = arrasteFolha.current;
      const el = folhaRef.current;
      if (!el) return;
      if (!a.moveu) {
        a.moveu = true;
        el.style.transition = "none";
      }
      a.pos = Math.min(alvosFolha().recolhida, Math.max(0, a.base + y - a.y0));
      el.style.transform = `translateY(${a.pos}px)`;
      a.amostras.push([performance.now(), y]);
      if (a.amostras.length > 6) a.amostras.shift();
    },
    [alvosFolha],
  );

  const terminarArraste = useCallback(
    (cancelado: boolean) => {
      const a = arrasteFolha.current;
      const el = folhaRef.current;
      const estava = a.ativo && a.moveu;
      a.ativo = false;
      if (!estava || !el) return;
      // Descarta o clique que vem logo depois do arraste; se ele não vier, a trava se desfaz.
      a.suprimirClique = true;
      setTimeout(() => (a.suprimirClique = false), 400);
      let destino: Folha = folhaAtual.current;
      if (!cancelado) {
        const alvos = alvosFolha();
        // Posições distintas, de cima (aberta) para baixo (recolhida).
        const ordem = (["aberta", "meia", "recolhida"] as Folha[]).filter(
          (f, i, l) => i === 0 || Math.abs(alvos[f] - alvos[l[i - 1]]) > 24,
        );
        const perto = (y: number) =>
          ordem.reduce((m, f) => (Math.abs(alvos[f] - y) < Math.abs(alvos[m] - y) ? f : m), ordem[0]);
        const [t0, y0] = a.amostras[0];
        const [t1, y1] = a.amostras[a.amostras.length - 1];
        const v = (y1 - y0) / Math.max(1, t1 - t0); // px/ms; positivo = para baixo
        const dy = a.pos - a.base;
        const i0 = ordem.indexOf(perto(a.base));
        if (Math.abs(v) > 0.5) {
          destino = ordem[Math.min(ordem.length - 1, Math.max(0, i0 + Math.sign(v)))];
        } else {
          destino = perto(a.pos);
          const vizinho = ordem[i0 + Math.sign(dy)];
          if (destino === ordem[i0] && vizinho && Math.abs(dy) > Math.abs(alvos[vizinho] - alvos[ordem[i0]]) * 0.3) {
            destino = vizinho;
          }
        }
      }
      // Tira o estilo do gesto: a transição da classe leva da posição atual até o destino.
      el.style.transition = "";
      el.style.transform = "";
      if (destino !== "aberta") el.scrollTop = 0;
      setFolha(destino);
    },
    [alvosFolha],
  );

  // Toque: eventos nativos (não passivos) na folha inteira, para decidir já no primeiro movimento
  // entre mover a folha e deixar o conteúdo rolar.
  useEffect(() => {
    const el = folhaRef.current;
    if (!el) return;
    const inicio = (e: TouchEvent) => {
      if (e.touches.length !== 1) return terminarArraste(true);
      comecarArraste(e.touches[0].clientY, topoFolhaRef.current?.contains(e.target as Node) ?? false);
    };
    const mover = (e: TouchEvent) => {
      const a = arrasteFolha.current;
      if (!a.ativo) return;
      if (e.touches.length !== 1) return terminarArraste(true);
      const y = e.touches[0].clientY;
      if (!a.decidido) {
        const dy = y - a.y0;
        if (Math.abs(dy) < 6) return;
        a.decidido = true;
        const arrasta = folhaAtual.current !== "aberta" || a.pelaAlca || (dy > 0 && el.scrollTop <= 0);
        if (!arrasta) {
          a.ativo = false; // o conteúdo rola normalmente
          return;
        }
      }
      if (e.cancelable) e.preventDefault();
      moverArraste(y);
    };
    const fim = (e: TouchEvent) => terminarArraste(e.type === "touchcancel");
    el.addEventListener("touchstart", inicio, { passive: true });
    el.addEventListener("touchmove", mover, { passive: false });
    el.addEventListener("touchend", fim);
    el.addEventListener("touchcancel", fim);
    return () => {
      el.removeEventListener("touchstart", inicio);
      el.removeEventListener("touchmove", mover);
      el.removeEventListener("touchend", fim);
      el.removeEventListener("touchcancel", fim);
    };
  }, [comecarArraste, moverArraste, terminarArraste]);

  // Mouse (janela estreita no computador): arrasta pela alça/cabeçalho.
  const aoApertarFolha = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType !== "mouse" || e.button !== 0) return;
    if (comecarArraste(e.clientY, true)) arrasteFolha.current.decidido = true;
  };
  const aoMoverFolha = (e: React.PointerEvent<HTMLDivElement>) => {
    const a = arrasteFolha.current;
    if (e.pointerType !== "mouse" || !a.ativo) return;
    if (!a.moveu && Math.abs(e.clientY - a.y0) < 6) return;
    if (!a.moveu) e.currentTarget.setPointerCapture(e.pointerId);
    moverArraste(e.clientY);
  };
  const aoSoltarFolha = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === "mouse") terminarArraste(e.type === "pointercancel");
  };

  // Voltando para a aba Mapa, reenquadra (o mapa escondido não tem tamanho).
  useEffect(() => {
    if (vista !== "mapa") return;
    const id = requestAnimationFrame(() => controle.current?.reenquadrar());
    return () => cancelAnimationFrame(id);
  }, [vista]);

  const migalhas = [
    { rotulo: "Início", href: "/" },
    { rotulo: "Impostos e repasses" },
  ];

  let cabecalho;
  let corpo;
  if (ibge) {
    cabecalho = (
      <CabecalhoCidade
        nome={nomeCidade}
        ufNome={ufNome}
        ano={anoMostrado}
        repasse={serieAno?.repasse ?? null}
        porMorador={serieAno?.por_habitante ?? null}
        populacao={serieAno?.populacao ?? porIbge.get(ibge)?.populacao ?? null}
        nota={notaPop}
      />
    );
    corpo = munOk ? (
      <>
        <Avisos avisos={avisoAnoEmCurso} />
        <CorpoCidade ibge={ibge} uf={uf ?? ""} ano={anoMostrado} mun={munOk} populacaoNota={notaPop} />
      </>
    ) : (
      <p className="text-sm text-muted-foreground">Carregando os repasses da cidade…</p>
    );
  } else if (uf && ufLinha) {
    cabecalho = <CabecalhoEstado uf={ufLinha} ano={anoMostrado} />;
    corpo = <CorpoEstado uf={ufLinha} painel={painel} estado={estadoOk} anos={anos} />;
  } else {
    cabecalho = <CabecalhoBrasil painel={painel} />;
    corpo = <CorpoBrasil painel={painel} />;
  }
  if (!cabecalho) cabecalho = <CabecalhoPainel sobre="Brasil" titulo="Todos os estados" chave="" />;

  const resumoOnde = (
    <>
      <button
        type="button"
        className={estilos.voltar}
        onClick={() => navegar(ibge ? { uf: uf ?? undefined } : {})}
      >
        <span aria-hidden>‹</span> {ibge ? ufNome : "Brasil"}
      </button>
      <span className={ibge ? `${estilos.onde} ${estilos.ondeCidade}` : estilos.onde}>
        {ibge ? (
          <>
            {ufNome} › <b>{nomeCidade}</b>
          </>
        ) : (
          <b>{ufNome}</b>
        )}
      </span>
    </>
  );

  const tituloMapa = uf
    ? `Mapa das cidades de ${ufNome}, colorido pelo repasse da União por habitante`
    : `Mapa do Brasil por estado, colorido por: ${NOME_INDICADOR[ind].toLowerCase()}`;

  return (
    <div ref={raizRef} data-largura="larga" className={`${estilos.raiz} ${ibge && folha === "meia" ? estilos.comMeia : ""}`}>
      <header className={estilos.topo}>
        <div className={estilos.migalhas}>
          <Migalhas itens={migalhas} />
        </div>
        <h1 className={`${estilos.h1} font-heading`}>
          <span className={estilos.longo}>Quanto a União arrecada e quanto repassa em cada estado</span>
          <span className={estilos.curto}>Imposto federal: o que sai e o que volta</span>
        </h1>
      </header>

      <div className={estilos.barra}>
        <div className={estilos.abas} role="tablist" aria-label="Forma de ver">
          <button type="button" role="tab" aria-selected={vista === "mapa"} onClick={() => setVista("mapa")}>
            Mapa
          </button>
          <button type="button" role="tab" aria-selected={vista === "lista"} onClick={() => setVista("lista")}>
            Lista
          </button>
        </div>
        {!uf && (
          <div className={estilos.chips} role="group" aria-label="O que as cores mostram">
            {INDICADORES.map((k) => (
              <button key={k} type="button" aria-pressed={ind === k} onClick={() => setInd(k)}>
                {NOME_INDICADOR[k]}
              </button>
            ))}
          </div>
        )}
        <select
          className={estilos.seletor}
          aria-label="Ano"
          value={ano}
          onChange={(e) => trocarAno(Number(e.target.value))}
        >
          {[...anos].reverse().map((a) => (
            <option key={a} value={a}>
              {rotuloAno(a, a === anos[anos.length - 1] && painel.ano_em_curso)}
            </option>
          ))}
        </select>
        <button
          type="button"
          className={estilos.lupa}
          aria-label="Buscar cidade"
          onClick={() => {
            setBuscaAberta(true);
            requestAnimationFrame(() => buscaRef.current?.querySelector("input")?.focus());
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-4-4" />
          </svg>
        </button>
        <div ref={buscaRef} className={`${estilos.buscaCx} ${buscaAberta ? estilos.buscaAberta : ""}`}>
          <BuscaCidade
            onEscolher={(u, i) => {
              setBuscaAberta(false);
              setVista("mapa");
              navegar({ uf: u, municipio: i });
            }}
          />
          <button type="button" className={estilos.fecharBusca} onClick={() => setBuscaAberta(false)}>
            Fechar
          </button>
        </div>
      </div>

      <div className={estilos.grade} aria-busy={carregando}>
        <div className={estilos.palco}>
          <div className={estilos.mapaCaixa} hidden={vista !== "mapa"}>
            <div className={estilos.mapaInterno}>
              <MapaBrasil
                niveis="municipio"
                uf={uf ?? undefined}
                municipio={ibge ?? undefined}
                onNavegar={navegar}
                classe={classeMapa}
                rotulo={rotuloMapa}
                resumo={resumoMapa}
                controle={controle}
                titulo={tituloMapa}
                prioridade={prioridadeMapa}
                className="h-full w-full"
              />
            </div>
            {uf && (
              <div className={estilos.sobre} data-mapa-evitar>
                {resumoOnde}
              </div>
            )}
            {uf && !ibge && (
              <div className={estilos.zoom} data-mapa-evitar>
                <button type="button" aria-label="Aproximar" onClick={() => controle.current?.zoom(1.5)}>
                  +
                </button>
                <button type="button" aria-label="Afastar" onClick={() => controle.current?.zoom(1 / 1.5)}>
                  −
                </button>
              </div>
            )}
          </div>
          <div className={`${estilosMapa.caixa} ${estilos.legenda}`} hidden={vista !== "mapa" || Boolean(ibge)}>
            {valoresLegenda.length > 0 && minimo != null && maximo != null ? (
              <>
                <span className={`${estilos.tituloLeg} ${nivelMun ? "" : estilos.trocaCel}`}>
                  {NOME_INDICADOR[indEfetivo]}, {anoMostrado}
                  {nivelMun ? `, cidades de ${ufNome}` : ""}
                </span>
                {!nivelMun && (
                  <label className={estilos.indCel}>
                    <span>Cores:</span>
                    <select
                      aria-label="O que as cores mostram"
                      value={ind}
                      onChange={(e) => setInd(e.target.value as Indicador)}
                    >
                      {INDICADORES.map((k) => (
                        <option key={k} value={k}>
                          {NOME_INDICADOR[k]}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {valorUnico ? (
                  <>
                    <div className={estilos.faixa} aria-hidden style={{ gridTemplateColumns: "1fr" }}>
                      <i style={{ background: "var(--mapa-3)" }} />
                    </div>
                    <div className={estilos.rotulos}>
                      <span>
                        {`${nomeUnico ?? (nivelMun ? "Todas as cidades" : "Todos os estados")}: `}
                        {rotulosLegenda[0]} {unidadeLegenda}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className={estilos.faixa} aria-hidden>
                      {[1, 2, 3, 4, 5].map((i) => (
                        <i key={i} style={{ background: `var(--mapa-${i})` }} />
                      ))}
                    </div>
                    <div className={estilos.rotulos}>
                      {rotulosLegenda.map((t, i) => (
                        <span key={`${i}-${t}`}>{t}</span>
                      ))}
                    </div>
                  </>
                )}
                <span className={estilos.legendaTexto}>
                  {valorUnico ? "" : `Cada cor reúne um quinto dos ${nivelMun ? "municípios" : "estados"}. `}Cinza: sem dado.
                  {nivelMun && ind !== "repHab"
                    ? " Nas cidades o mapa mostra o repasse por habitante: a Receita Federal não publica arrecadação por cidade."
                    : ""}
                </span>
              </>
            ) : (
              <span>
                {nivelMun && !estadoOk ? "Carregando as cidades…" : `Sem dado de ${NOME_INDICADOR[indEfetivo].toLowerCase()} em ${anoMostrado}.`}
              </span>
            )}
          </div>
          {vista === "lista" && (
            <ListaLugares
              nivel={nivelMun ? "mun" : "uf"}
              linhas={linhas}
              legenda={
                nivelMun
                  ? `As ${linhas.length.toLocaleString("pt-BR")} cidades de ${ufNome}, ${anoMostrado}.`
                  : `Os ${linhas.length} estados, ${anoMostrado}.`
              }
              onEscolher={(id) => {
                setVista("mapa");
                navegar(nivelMun && uf ? { uf, municipio: id } : { uf: id });
              }}
            />
          )}
        </div>

        <aside
          ref={folhaRef}
          className={`${estilos.painel} ${folha !== "recolhida" ? estilos[folha] : ""}`}
          aria-label="Números do lugar escolhido"
          aria-live="polite"
        >
          <div
            ref={topoFolhaRef}
            className={estilos.cabecalhoToque}
            onClick={() => {
              if (arrasteFolha.current.suprimirClique) {
                arrasteFolha.current.suprimirClique = false;
                return;
              }
              setFolha((f) => (f !== "recolhida" ? "recolhida" : ibge ? "meia" : "aberta"));
            }}
            onPointerDown={aoApertarFolha}
            onPointerMove={aoMoverFolha}
            onPointerUp={aoSoltarFolha}
            onPointerCancel={aoSoltarFolha}
          >
            <button
              type="button"
              className={estilos.alca}
              aria-expanded={folha !== "recolhida"}
              aria-controls="corpo-painel-dinheiro"
            >
              <i />
              <span>{folha !== "recolhida" ? "Fechar" : "Puxe para ver mais"}</span>
            </button>
            <div className={estilos.cabFolha}>{cabecalho}</div>
          </div>
          <div id="corpo-painel-dinheiro" className={estilos.corpo}>
            {erro && (
              <p role="alert" className="text-sm text-muted-foreground">
                Não foi possível carregar esses números agora: {erro}
              </p>
            )}
            {corpo}
            <div className={estilos.soMobile}>
              <Secao titulo="Fontes e notas">
                <Fontes fontes={fontes} />
              </Secao>
            </div>
          </div>
        </aside>
      </div>

      <footer className={`${estilos.soDesk} max-w-3xl`}>
        <Fontes fontes={fontes} />
      </footer>
    </div>
  );
}
