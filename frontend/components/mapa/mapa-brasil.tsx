"use client";

// Mapa Brasil -> estado -> cidade (portado do protótipo aprovado). Quem controla a URL é a página:
// o lugar atual vem por props e as mudanças saem por onNavegar. Malhas em /mapa (IBGE).

import {
  memo,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useId,
  useState,
  type ReactNode,
  type Ref,
} from "react";
import {
  CAIXA_BRASIL,
  carregarDetalhe,
  carregarMunicipios,
  carregarUfs,
  SIGLA_FORA,
  type Caixa,
  type ClasseMapa,
  type Lugar,
  type MalhaMun,
  type MalhaUf,
  type NivelMapa,
} from "@/lib/mapa";
import { buscarNoMapa, moverNoMapa, ordenarPorNome, TECLAS_MAPA, type ItemMapa, type TeclaMapa } from "@/lib/navegar-mapa";
import { UFS } from "@/lib/ufs";
import estilos from "./mapa-brasil.module.css";

const NOME_UF = new Map(UFS.map((u) => [u.sigla, u.nome]));

type Vb = [number, number, number, number];
type Alvo = { nivel: NivelMapa; id: string };

export interface MapaControle {
  zoom: (fator: number) => void;
  reenquadrar: () => void;
}

export interface MapaBrasilProps {
  /** "uf": só estados (clicar chama onNavegar sem aproximar). "municipio": Brasil -> UF -> cidade. */
  niveis: "uf" | "municipio";
  uf?: string;
  municipio?: string;
  onNavegar: (lugar: Lugar) => void;
  /** Classe de cor 0..5 (0 = sem dado). */
  classe: (nivel: NivelMapa, id: string) => ClasseMapa;
  /** Nome falado ao leitor de tela (e rótulo da região). */
  rotulo: (nivel: NivelMapa, id: string) => string;
  /** Conteúdo da dica que segue o mouse. */
  resumo?: (nivel: NivelMapa, id: string) => ReactNode;
  /** Um toque já entra (padrão). Com false: o 1º toque seleciona, o 2º entra. */
  toqueUnico?: boolean;
  onSelecionar?: (alvo: Alvo | null) => void;
  /** Para os botões +/-: controle.current.zoom(1.5) e zoom(1 / 1.5). */
  controle?: Ref<MapaControle>;
  className?: string;
  /** Descrição do mapa para leitor de tela. */
  titulo?: string;
  /** Ordem dos nomes das cidades ao aproximar (ex.: população); maior aparece primeiro. Sem ela,
   * só ganham nome as cidades cujo desenho comporta o texto, das maiores para as menores. */
  prioridade?: (ibge: string) => number | null | undefined;
}

// Rótulos: tamanho fixo na tela (px), desenhados numa camada por cima, sem receber toque.
const FONTE_UF = 11;
const FONTE_MUN = 12;
const FONTE_CIDADE = 13;
const ALTURA = (f: number) => f + 2;
type Retangulo = [number, number, number, number];
const colide = (a: Retangulo, b: Retangulo) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];

let medidor: CanvasRenderingContext2D | null = null;
const larguras = new Map<string, number>();
function larguraTexto(texto: string, fonte: string): number {
  const chave = `${fonte}|${texto}`;
  let w = larguras.get(chave);
  if (w == null) {
    medidor ??= document.createElement("canvas").getContext("2d");
    if (medidor) {
      medidor.font = fonte;
      w = medidor.measureText(texto).width;
    } else {
      w = texto.length * 7;
    }
    larguras.set(chave, w);
  }
  return w;
}

const SVG_NS = "http://www.w3.org/2000/svg";
function texto(x: number, y: number, conteudo: string, classe: string): SVGTextElement {
  const t = document.createElementNS(SVG_NS, "text");
  t.setAttribute("x", x.toFixed(1));
  t.setAttribute("y", y.toFixed(1));
  t.setAttribute("class", classe);
  t.textContent = conteudo;
  return t;
}

interface CaminhoProps {
  d: string;
  nivel: NivelMapa;
  id: string;
  c: number;
  rotulo: string;
  ativa: boolean;
  sel: boolean;
  sobre: boolean;
  /** Fora de uso (outro nível do mapa): sai da árvore de acessibilidade e da ordem de Tab. */
  oculto: boolean;
  /** A única parada de Tab do mapa (roving tabindex); os demais recebem foco pelas setas. */
  daVez: boolean;
}

const Caminho = memo(function Caminho({ d, nivel, id, c, rotulo, ativa, sel, sobre, oculto, daVez }: CaminhoProps) {
  const cls = [estilos[nivel], ativa && estilos.ativa, sel && estilos.sel, sobre && estilos.sobre]
    .filter(Boolean)
    .join(" ");
  return (
    <path
      d={d}
      className={cls}
      data-id={id}
      data-nivel={nivel}
      data-c={c}
      tabIndex={!oculto && daVez ? 0 : -1}
      role="button"
      aria-label={rotulo}
      aria-hidden={oculto ? "true" : undefined}
    />
  );
});

function caixaPara(svg: SVGSVGElement | null, b: Caixa, folga = 0.08): Vb {
  const [x0, y0, x1, y1] = b;
  const rc = svg?.getBoundingClientRect();
  const w = x1 - x0;
  const h = y1 - y0;
  const r = rc ? rc.width / Math.max(1, rc.height) || 1 : 1;
  let W = w * (1 + folga * 2);
  let H = h * (1 + folga * 2);
  if (W / H < r) W = H * r;
  else H = W / r;
  return [x0 + w / 2 - W / 2, y0 + h / 2 - H / 2, W, H];
}

const mesmo = (a: Alvo | null, b: Alvo | null) => a?.nivel === b?.nivel && a?.id === b?.id;

export function MapaBrasil({
  niveis,
  uf,
  municipio,
  onNavegar,
  classe,
  rotulo,
  resumo,
  toqueUnico = true,
  onSelecionar,
  controle,
  className,
  titulo = "Mapa do Brasil",
  prioridade,
}: MapaBrasilProps) {
  const [ufs, setUfs] = useState<MalhaUf | null>(null);
  const [muns, setMuns] = useState<{ uf: string; geo: MalhaMun } | null>(null);
  const [detalhe, setDetalhe] = useState<{ id: string; d: string } | null>(null);
  const [erro, setErro] = useState(false);
  const [sobre, setSobre] = useState<Alvo | null>(null);
  const [dica, setDica] = useState<Alvo | null>(null);
  const [sel, setSel] = useState<Alvo | null>(null);
  // Roving tabindex: último item que recebeu foco (vale enquanto estiver no nível atual).
  const [daVez, setDaVez] = useState<Alvo | null>(null);
  // Item com foco de teclado agora (contorno de foco e anúncio); null quando o foco sai do mapa.
  const [comFoco, setComFoco] = useState<Alvo | null>(null);
  // Página ampliada pela pinça (visualViewport.scale > 1): o mapa cede o gesto ao navegador.
  const [ampliada, setAmpliada] = useState(false);
  const idInstrucao = useId();

  // Em "uf" o mapa nunca aproxima; o lugar vem só para destacar.
  const ufEf = niveis === "municipio" ? uf : undefined;
  const munEf = ufEf ? municipio : undefined;

  const svgRef = useRef<SVGSVGElement>(null);
  const caixaRef = useRef<HTMLDivElement>(null);
  const dicaRef = useRef<HTMLDivElement>(null);
  const vb = useRef<Vb>([...CAIXA_BRASIL]);
  const anim = useRef(0);
  const pos = useRef({ x: 0, y: 0 });
  const ponteiros = useRef(new Map<number, [number, number]>());
  const arrastando = useRef(false);
  const ampliadaRef = useRef(false);
  // Depois de Enter/Esc pelo teclado, o foco vai para o item da vez do nível novo.
  const levarFoco = useRef(false);
  const digitado = useRef({ texto: "", t: 0 });
  // Instante do último pointerup/keydown tratado: o `click` que o navegador dispara logo depois
  // não pode abrir de novo. Click sem ponteiro antes (leitor de tela) abre normalmente.
  const ultimoToque = useRef(0);
  const inicio = useRef<{ x: number; y: number; vb: Vb; d: number | null; cx: number; cy: number }>({
    x: 0,
    y: 0,
    vb: [...CAIXA_BRASIL],
    d: null,
    cx: 0,
    cy: 0,
  });
  const rotulosRef = useRef<SVGSVGElement>(null);
  const quadroRotulos = useRef(0);
  // Valores atuais para handlers nativos e callbacks estáveis.
  const atual = useRef({ ufEf, munEf, ufs, muns, onNavegar, onSelecionar, prioridade });
  useEffect(() => {
    atual.current = { ufEf, munEf, ufs, muns, onNavegar, onSelecionar, prioridade };
  });

  // ---- rótulos (siglas no Brasil, nomes das cidades ao aproximar) ----
  // Recalculados no máximo uma vez por quadro, sempre que o viewBox, o tamanho ou a malha mudam.
  const desenharRotulosAgora = useCallback(() => {
    const camada = rotulosRef.current;
    const svg = svgRef.current;
    const caixa = caixaRef.current;
    if (!camada || !svg || !caixa) return;
    const { ufEf, munEf, ufs, muns, prioridade } = atual.current;
    const r = svg.getBoundingClientRect();
    const c = caixa.getBoundingClientRect();
    const W = r.width;
    const H = r.height;
    const novos: SVGElement[] = [];
    if (!ufs || W < 10 || H < 10) return camada.replaceChildren();
    const [vx, vy, vw, vh] = vb.current;
    const esc = Math.max(vw / W, vh / H);
    const ox = vx - (W * esc - vw) / 2;
    const oy = vy - (H * esc - vh) / 2;
    const dx = r.left - c.left;
    const dy = r.top - c.top;
    const tela = (x: number, y: number): [number, number] => [(x - ox) / esc + dx, (y - oy) / esc + dy];
    const familia = getComputedStyle(caixa).fontFamily;

    // Áreas que os nomes não podem cobrir (botões e avisos sobre o mapa), em px da caixa.
    const ocupados: Retangulo[] = [];
    const area = caixa.parentElement?.parentElement ?? caixa;
    area.querySelectorAll<HTMLElement>("[data-mapa-evitar]").forEach((el) => {
      const filhos = el.children.length ? Array.from(el.children) : [el];
      for (const f of filhos) {
        const b = f.getBoundingClientRect();
        if (b.width && b.height) ocupados.push([b.left - c.left - 4, b.top - c.top - 4, b.right - c.left + 4, b.bottom - c.top + 4]);
      }
    });

    if (!ufEf) {
      const fonte = `600 ${FONTE_UF}px ${familia}`;
      for (const [sigla, g] of Object.entries(ufs)) {
        if (!g.l) continue;
        const [lx, ly] = tela(g.l[0], g.l[1]);
        const w = larguraTexto(sigla, fonte);
        const raio = g.l[2] / esc;
        const fora = SIGLA_FORA[sigla];
        if (raio * 2 >= w + 4 || !fora) {
          novos.push(texto(lx, ly, sigla, estilos.sigla));
          continue;
        }
        const [fx, fy] = tela(fora[0], fora[1]);
        // linha do estado até a borda do rótulo
        const ang = Math.atan2(ly - fy, lx - fx);
        const meiaL = w / 2 + 3;
        const meiaA = ALTURA(FONTE_UF) / 2 + 1;
        const k = Math.min(meiaL / Math.max(0.01, Math.abs(Math.cos(ang))), meiaA / Math.max(0.01, Math.abs(Math.sin(ang))));
        const linha = document.createElementNS(SVG_NS, "path");
        linha.setAttribute(
          "d",
          `M${lx.toFixed(1)} ${ly.toFixed(1)}L${(fx + Math.cos(ang) * k).toFixed(1)} ${(fy + Math.sin(ang) * k).toFixed(1)}`,
        );
        linha.setAttribute("class", estilos.guia);
        const ponto = document.createElementNS(SVG_NS, "circle");
        ponto.setAttribute("cx", lx.toFixed(1));
        ponto.setAttribute("cy", ly.toFixed(1));
        ponto.setAttribute("r", "1.6");
        ponto.setAttribute("class", estilos.guiaPonto);
        novos.push(linha, ponto, texto(fx, fy, sigla, estilos.sigla));
      }
    } else if (muns?.uf === ufEf) {
      const geo = muns.geo;
      if (munEf) {
        const m = geo[munEf];
        if (m) {
          const p = m.l ?? [(m.b[0] + m.b[2]) / 2, (m.b[1] + m.b[3]) / 2, 0];
          const [lx, ly] = tela(p[0], p[1]);
          const w = larguraTexto(m.n, `600 ${FONTE_CIDADE}px ${familia}`);
          // dentro da caixa e longe dos botões; se colidir, sobe para acima do desenho
          let y = ly;
          const caixaTexto = (yy: number): Retangulo => [lx - w / 2 - 3, yy - 9, lx + w / 2 + 3, yy + 9];
          if (ocupados.some((o) => colide(o, caixaTexto(y)))) y = tela(0, m.b[1])[1] - 12;
          const x = Math.min(W - w / 2 - 4, Math.max(w / 2 + 4, lx));
          novos.push(texto(x, Math.max(14, Math.min(H - 6, y)), m.n, `${estilos.nome} ${estilos.nomeCidade}`));
        }
      } else {
        const fonte = `600 ${FONTE_MUN}px ${familia}`;
        const h = ALTURA(FONTE_MUN);
        const cands: Array<{ x: number; y: number; n: string; w: number; p: number }> = [];
        for (const [cod, m] of Object.entries(geo)) {
          if (!m.l) continue;
          const [lx, ly] = tela(m.l[0], m.l[1]);
          if (lx < 0 || ly < 0 || lx > W || ly > H) continue;
          const raio = m.l[2] / esc;
          const largura = (m.b[2] - m.b[0]) / esc;
          const w = larguraTexto(m.n, fonte);
          const cabe = raio * 2 >= h - 2 && w <= Math.max(raio * 2.2, largura * 0.9);
          const pop = prioridade?.(cod);
          // Com prioridade, as cidades maiores ganham nome mesmo um pouco além do desenho,
          // desde que ele não seja minúsculo na tela.
          // Sem prioridade, cidades de desenho médio também ganham nome (das maiores para as menores).
          if (!cabe && !(pop != null ? raio * 2 >= 3 : raio * 2 >= 9)) continue;
          cands.push({ x: lx, y: ly, n: m.n, w, p: pop != null ? pop : -1 / Math.max(raio, 1e-6) });
        }
        cands.sort((a, b) => b.p - a.p);
        const limite = Math.max(6, Math.floor((W * H) / 9000));
        const postos: Retangulo[] = [];
        for (const k of cands) {
          if (postos.length >= limite) break;
          const caixaTexto: Retangulo = [k.x - k.w / 2 - 3, k.y - h / 2 - 2, k.x + k.w / 2 + 3, k.y + h / 2 + 2];
          if (caixaTexto[0] < 2 || caixaTexto[2] > W - 2 || caixaTexto[1] < 2 || caixaTexto[3] > H - 2) continue;
          if (postos.some((o) => colide(o, caixaTexto)) || ocupados.some((o) => colide(o, caixaTexto))) continue;
          postos.push(caixaTexto);
          novos.push(texto(k.x, k.y, k.n, estilos.nome));
        }
      }
    }
    camada.replaceChildren(...novos);
  }, []);
  const desenharRotulos = useCallback(() => {
    quadroRotulos.current = 0;
    try {
      desenharRotulosAgora();
    } catch (erro) {
      // Nunca deixa rótulos velhos parados por cima do mapa.
      rotulosRef.current?.replaceChildren();
      console.error("Rótulos do mapa:", erro);
    }
  }, [desenharRotulosAgora]);

  const agendarRotulos = useCallback(() => {
    if (!quadroRotulos.current) quadroRotulos.current = requestAnimationFrame(desenharRotulos);
  }, [desenharRotulos]);
  // Ao esconder a página (Activity) ou desmontar: cancela o quadro pendente e zera a marca. Sem
  // zerar, a marca ficava presa e os rótulos nunca mais eram redesenhados (siglas do Brasil
  // paradas por cima do estado).
  useEffect(
    () => () => {
      cancelAnimationFrame(quadroRotulos.current);
      quadroRotulos.current = 0;
    },
    [],
  );

  const setVB = useCallback(
    (v: Vb) => {
      vb.current = v;
      svgRef.current?.setAttribute("viewBox", v.map((x) => x.toFixed(2)).join(" "));
      agendarRotulos();
    },
    [agendarRotulos],
  );

  const enquadrar = useCallback((): Vb => {
    const { ufEf, munEf, ufs, muns } = atual.current;
    if (!ufEf || !ufs?.[ufEf]) return [...CAIXA_BRASIL];
    const m = munEf && muns?.uf === ufEf ? muns.geo[munEf] : undefined;
    return m ? caixaPara(svgRef.current, m.b, 0.12) : caixaPara(svgRef.current, ufs[ufEf].bbox);
  }, []);

  const animarPara = useCallback(
    (alvo: Vb, ms = 520) => {
      const ini = [...vb.current] as Vb;
      const t0 = performance.now();
      const id = ++anim.current;
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) return setVB(alvo);
      const passo = (t: number) => {
        if (id !== anim.current) return;
        let k = Math.min(1, (t - t0) / ms);
        k = 1 - Math.pow(1 - k, 3);
        setVB(ini.map((x, i) => x + (alvo[i] - x) * k) as Vb);
        if (k < 1) requestAnimationFrame(passo);
      };
      requestAnimationFrame(passo);
      // Garante o enquadramento final se o navegador pausar os quadros (aba em segundo plano).
      setTimeout(() => {
        if (id === anim.current) setVB(alvo);
      }, ms + 80);
    },
    [setVB],
  );

  // ---- carga das malhas ----
  useEffect(() => {
    let vivo = true;
    carregarUfs()
      .then((g) => vivo && setUfs(g))
      .catch(() => vivo && setErro(true));
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    if (!ufEf) return;
    let vivo = true;
    carregarMunicipios(ufEf)
      .then((geo) => vivo && setMuns({ uf: ufEf, geo }))
      .catch(() => vivo && setErro(true));
    return () => {
      vivo = false;
    };
  }, [ufEf]);

  // Cidade aberta sozinha: troca o desenho simplificado pelo detalhado (sob demanda).
  useEffect(() => {
    if (!ufEf || !munEf) return;
    let vivo = true;
    carregarDetalhe(ufEf)
      .then((det) => vivo && det[munEf] && setDetalhe({ id: munEf, d: det[munEf] }))
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, [ufEf, munEf]);

  // ---- enquadramento quando o lugar (ou a malha) muda ----
  const munPronto = muns && muns.uf === ufEf ? muns : null;
  useEffect(() => {
    if (!ufs) return;
    animarPara(enquadrar());
  }, [ufs, ufEf, munEf, munPronto, enquadrar, animarPara]);

  // Mudou o lugar: limpa seleção e dica (ajuste durante a renderização, sem efeito).
  const chaveLugar = `${ufEf ?? ""}-${munEf ?? ""}`;
  const [chaveVista, setChaveVista] = useState(chaveLugar);
  if (chaveVista !== chaveLugar) {
    setChaveVista(chaveLugar);
    setSel(null);
    setDica(null);
  }

  useEffect(() => {
    // No celular a barra do navegador muda a altura sozinha: só reenquadra (e desfaz o zoom) se
    // a largura mudar ou a altura mudar muito.
    let ultimo = [innerWidth, innerHeight];
    const aoRedimensionar = () => {
      const mudou = innerWidth !== ultimo[0] || Math.abs(innerHeight - ultimo[1]) > 160;
      ultimo = [innerWidth, innerHeight];
      if (mudou && !arrastando.current) setVB(enquadrar());
      else agendarRotulos();
    };
    addEventListener("resize", aoRedimensionar);
    return () => removeEventListener("resize", aoRedimensionar);
  }, [enquadrar, setVB, agendarRotulos]);

  // A caixa muda de tamanho sem a janela mudar (folha de baixo, abas): redesenha os rótulos.
  useEffect(() => {
    const caixa = caixaRef.current;
    if (!caixa) return;
    const ro = new ResizeObserver(agendarRotulos);
    ro.observe(caixa);
    return () => ro.disconnect();
  }, [agendarRotulos]);
  // Malha, lugar ou prioridade mudaram: redesenha (no máximo uma vez por quadro).
  useEffect(agendarRotulos);

  // ---- zoom (roda, pinça, botões) ----
  const zoomEm = useCallback(
    (cx: number, cy: number, fator: number) => {
      const { ufEf, ufs } = atual.current;
      const svg = svgRef.current;
      if (!ufEf || !ufs?.[ufEf] || !svg) return;
      const [x, y, w0, h0] = vb.current;
      const r = svg.getBoundingClientRect();
      const esc = Math.max(w0 / r.width, h0 / r.height);
      const px = x - (r.width * esc - w0) / 2 + (cx - r.left) * esc;
      const py = y - (r.height * esc - h0) / 2 + (cy - r.top) * esc;
      const lim = caixaPara(svg, ufs[ufEf].bbox, 0.3);
      // Aproxima até 1/25 do estado, ou até 1/4 do enquadramento da cidade se ela for menor.
      const minimo = Math.min(lim[2] / 25, enquadrar()[2] / 4);
      const w = Math.min(lim[2], Math.max(minimo, w0 / fator));
      const k = w / w0;
      anim.current++;
      setVB([px - (px - x) * k, py - (py - y) * k, w, h0 * k]);
    },
    [setVB, enquadrar],
  );

  /** Desloca a vista em px de tela (arraste e pinça). */
  const moverPx = useCallback(
    (dx: number, dy: number) => {
      const svg = svgRef.current;
      if (!svg || (!dx && !dy)) return;
      const [x, y, w, h] = vb.current;
      const r = svg.getBoundingClientRect();
      const esc = Math.max(w / r.width, h / r.height);
      anim.current++;
      setVB([x - dx * esc, y - dy * esc, w, h]);
    },
    [setVB],
  );

  useImperativeHandle(
    controle,
    () => ({
      zoom: (f: number) => {
        const r = svgRef.current?.getBoundingClientRect();
        if (r) zoomEm(r.left + r.width / 2, r.top + r.height / 2, f);
      },
      reenquadrar: () => animarPara(enquadrar()),
    }),
    [zoomEm, animarPara, enquadrar],
  );

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const roda = (e: WheelEvent) => {
      if (!atual.current.ufEf) return; // no Brasil a página rola normalmente
      e.preventDefault();
      zoomEm(e.clientX, e.clientY, e.deltaY < 0 ? 1.25 : 0.8);
    };
    // Reforço ao touch-action: dentro do estado, com a página sem ampliação, dois dedos são a
    // pinça do mapa e não dão zoom na página (Safari dispara gesturestart; os outros, touchmove
    // com dois toques). Com a página já ampliada, o gesto fica com o navegador (ver touchAction).
    const toque = (e: TouchEvent) => {
      if (atual.current.ufEf && !ampliadaRef.current && e.touches.length > 1 && e.cancelable) e.preventDefault();
    };
    const gesto = (e: Event) => {
      if (atual.current.ufEf && !ampliadaRef.current) e.preventDefault();
    };
    svg.addEventListener("wheel", roda, { passive: false });
    svg.addEventListener("touchmove", toque, { passive: false });
    svg.addEventListener("gesturestart", gesto);
    return () => {
      svg.removeEventListener("wheel", roda);
      svg.removeEventListener("touchmove", toque);
      svg.removeEventListener("gesturestart", gesto);
    };
  }, [zoomEm, ufs]);

  // Quem ampliou a página com a pinça precisa conseguir desfazer (ou mover) a ampliação com os
  // dedos por cima do mapa, que no celular ocupa quase a tela toda.
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const medir = () => {
      const sim = vv.scale > 1.01;
      ampliadaRef.current = sim;
      setAmpliada(sim);
    };
    medir();
    vv.addEventListener("resize", medir);
    return () => vv.removeEventListener("resize", medir);
  }, []);

  // ---- alvo, seleção e ativação ----
  const alvoDe = (e: { target: EventTarget | null }): Alvo | null => {
    const t = (e.target as Element | null)?.closest?.("[data-id]") as SVGElement | null;
    if (!t || !svgRef.current?.contains(t)) return null;
    const id = t.dataset.id!;
    if (t.dataset.nivel === "mun") return { nivel: "mun", id };
    if (!atual.current.ufEf) return { nivel: "uf", id };
    return null;
  };
  const selecionar = (a: Alvo | null) => {
    setSel(a);
    atual.current.onSelecionar?.(a);
  };
  const ativar = (a: Alvo) => {
    if (a.nivel === "uf") atual.current.onNavegar({ uf: a.id });
    else atual.current.onNavegar({ uf: atual.current.ufEf, municipio: a.id });
  };
  const tocar = (a: Alvo | null, tipo: string) => {
    if (!a) {
      if (tipo !== "mouse") selecionar(null);
      return;
    }
    if (tipo === "mouse" || toqueUnico) return ativar(a);
    if (sel && sel.nivel === a.nivel && sel.id === a.id) return ativar(a);
    selecionar(a);
  };

  // ---- dica que segue o cursor ----
  const posicionarDica = useCallback(() => {
    const d = dicaRef.current;
    const caixa = caixaRef.current;
    if (!d || !caixa || d.hidden) return;
    const c = caixa.getBoundingClientRect();
    const w = d.offsetWidth;
    const h = d.offsetHeight;
    let lx = pos.current.x - c.left + 16;
    let ly = pos.current.y - c.top + 16;
    if (lx + w > c.width - 4) lx = pos.current.x - c.left - w - 16;
    if (ly + h > c.height - 4) ly = pos.current.y - c.top - h - 16;
    d.style.transform = `translate(${Math.max(4, lx)}px, ${Math.max(4, ly)}px)`;
  }, []);
  useLayoutEffect(posicionarDica, [dica, posicionarDica]);

  // ---- ponteiros: hover, arraste, pinça ----
  // Um dedo arrasta; dois dedos aproximam/afastam em torno do ponto médio (e o ponto médio
  // arrasta junto). Ao tirar um dos dois, o arraste recomeça do dedo que ficou, na vista atual:
  // antes ele recomeçava da vista de antes da pinça e desfazia o zoom.
  const reiniciarGesto = () => {
    const pts = [...ponteiros.current.values()];
    const ini = inicio.current;
    ini.vb = [...vb.current];
    ini.d = null;
    if (pts.length >= 2) {
      const [a, b] = pts;
      ini.d = Math.hypot(a[0] - b[0], a[1] - b[1]) || null;
      ini.cx = (a[0] + b[0]) / 2;
      ini.cy = (a[1] + b[1]) / 2;
    } else if (pts.length === 1) {
      ini.x = pts[0][0];
      ini.y = pts[0][1];
    }
  };
  const aoMover = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.pointerType === "mouse" && !arrastando.current) {
      const a = alvoDe(e);
      pos.current = { x: e.clientX, y: e.clientY };
      setSobre((s) => (mesmo(s, a) ? s : a));
      setDica((s) => (mesmo(s, a) ? s : a));
      posicionarDica();
    }
    if (!ponteiros.current.has(e.pointerId) || !atual.current.ufEf) return;
    ponteiros.current.set(e.pointerId, [e.clientX, e.clientY]);
    const ini = inicio.current;
    if (ponteiros.current.size >= 2) {
      const [a, b] = [...ponteiros.current.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const cx = (a[0] + b[0]) / 2;
      const cy = (a[1] + b[1]) / 2;
      if (ini.d && d) {
        zoomEm(cx, cy, d / ini.d);
        moverPx(cx - ini.cx, cy - ini.cy);
      }
      ini.d = d || null;
      ini.cx = cx;
      ini.cy = cy;
      return;
    }
    const dx = e.clientX - ini.x;
    const dy = e.clientY - ini.y;
    if (!arrastando.current && Math.hypot(dx, dy) < 8) return;
    if (!arrastando.current) svgRef.current?.setPointerCapture(e.pointerId);
    arrastando.current = true;
    setDica(null);
    const r = svgRef.current!.getBoundingClientRect();
    const esc = Math.max(ini.vb[2] / r.width, ini.vb[3] / r.height);
    anim.current++;
    setVB([ini.vb[0] - dx * esc, ini.vb[1] - dy * esc, ini.vb[2], ini.vb[3]]);
  };
  const aoApertar = (e: React.PointerEvent<SVGSVGElement>) => {
    ponteiros.current.set(e.pointerId, [e.clientX, e.clientY]);
    if (ponteiros.current.size === 1) {
      arrastando.current = false;
      inicio.current = { x: e.clientX, y: e.clientY, vb: [...vb.current], d: null, cx: 0, cy: 0 };
      return;
    }
    // Segundo dedo: é pinça; nada de toque/navegação ao soltar.
    arrastando.current = true;
    setDica(null);
    reiniciarGesto();
  };
  const aoSoltar = (e: React.PointerEvent<SVGSVGElement>) => {
    const era = arrastando.current;
    if (!ponteiros.current.delete(e.pointerId)) return;
    if (ponteiros.current.size) {
      reiniciarGesto(); // continua do jeito que está, com o(s) dedo(s) que ficou(aram)
      return;
    }
    arrastando.current = false;
    ultimoToque.current = performance.now();
    if (e.type === "pointerup" && !era) tocar(alvoDe(e), e.pointerType);
  };
  // Leitores de tela ativam com `click`, sem pointerup antes.
  const aoClicar = (e: React.MouseEvent<SVGSVGElement>) => {
    if (performance.now() - ultimoToque.current < 700) return;
    const a = alvoDe(e);
    if (a) ativar(a);
  };
  const aoSair = () => {
    setSobre(null);
    setDica(null);
  };

  // ---- teclado ----
  const alvoDoElemento = (el: EventTarget): Alvo | null => {
    const t = (el as Element).closest?.("[data-id]") as SVGElement | null;
    return t ? { nivel: t.dataset.nivel === "mun" ? "mun" : "uf", id: t.dataset.id! } : null;
  };
  // Itens do nível atual em ordem alfabética: é a ordem das setas e da busca por letras.
  const siglas = useMemo(() => (ufs ? Object.keys(ufs) : []), [ufs]);
  const nivelItens: NivelMapa = ufEf ? "mun" : "uf";
  const itens = useMemo((): ItemMapa[] => {
    if (!ufEf) return ordenarPorNome(siglas.map((s) => ({ id: s, nome: NOME_UF.get(s) ?? s })));
    if (!munPronto) return [];
    if (munEf) return munPronto.geo[munEf] ? [{ id: munEf, nome: munPronto.geo[munEf].n }] : [];
    return ordenarPorNome(Object.entries(munPronto.geo).map(([id, m]) => ({ id, nome: m.n })));
  }, [siglas, ufEf, munEf, munPronto]);
  const nomesItens = useMemo(() => itens.map((x) => x.nome), [itens]);
  // A parada de Tab: o último item focado neste nível; senão o selecionado; senão o lugar aberto
  // (ou destacado); senão o primeiro em ordem alfabética.
  const idDaVez = useMemo(() => {
    const tem = (id: string | undefined) => (id && itens.some((x) => x.id === id) ? id : undefined);
    const doNivel = (a: Alvo | null) => (a?.nivel === nivelItens ? a.id : undefined);
    return tem(doNivel(daVez)) ?? tem(doNivel(sel)) ?? tem(ufEf ? munEf : uf) ?? itens[0]?.id;
  }, [itens, nivelItens, daVez, sel, ufEf, munEf, uf]);

  // Depois de abrir ou voltar pelo teclado, o foco segue para o item da vez do nível novo (o
  // anterior saiu da vista). Só se o foco ainda está no mapa ou perdido no corpo da página.
  useEffect(() => {
    if (!levarFoco.current || !idDaVez) return;
    const ativo = document.activeElement;
    if (ativo && ativo !== document.body && !svgRef.current?.contains(ativo)) {
      levarFoco.current = false;
      return;
    }
    const el = svgRef.current?.querySelector<SVGPathElement>(`path[data-nivel="${nivelItens}"][data-id="${idDaVez}"]`);
    if (!el || el === ativo) return;
    levarFoco.current = false;
    el.focus({ preventScroll: true });
  }, [idDaVez, nivelItens]);

  /** Cidade fora da vista (estado aproximado): desloca o mapa até ela, sem mudar o zoom. */
  const garantirVisivel = (a: Alvo) => {
    const m = a.nivel === "mun" ? munPronto?.geo[a.id] : undefined;
    if (!m) return;
    const [x, y, w, h] = vb.current;
    const [x0, y0, x1, y1] = m.b;
    if (x0 >= x && x1 <= x + w && y0 >= y && y1 <= y + h) return;
    animarPara([(x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h], 260);
  };
  /** Leva o foco a um item (setas, Home/End, letras); o onFocus seleciona e anuncia. */
  const focarItem = (item: ItemMapa) => {
    const a: Alvo = { nivel: nivelItens, id: item.id };
    setDaVez(a);
    garantirVisivel(a);
    svgRef.current
      ?.querySelector<SVGPathElement>(`path[data-nivel="${a.nivel}"][data-id="${a.id}"]`)
      ?.focus({ preventScroll: true });
  };
  const aoTeclar = (e: React.KeyboardEvent<SVGSVGElement>) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const a = alvoDoElemento(e.target);
    if (!a) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      ultimoToque.current = performance.now();
      levarFoco.current = true;
      ativar(a);
      return;
    }
    if (e.key === "Escape") {
      const { ufEf, munEf } = atual.current;
      if (!ufEf) {
        // Brasil (ou mapa só de estados): não há nível acima; Esc só tira a seleção.
        if (sel) {
          e.preventDefault();
          selecionar(null);
        }
        return;
      }
      e.preventDefault();
      // Volta um nível e devolve o foco a quem estava aberto (a cidade, ou o estado).
      setDaVez(munEf ? { nivel: "mun", id: munEf } : { nivel: "uf", id: ufEf });
      levarFoco.current = true;
      atual.current.onNavegar(munEf ? { uf: ufEf } : {});
      return;
    }
    const i = itens.findIndex((x) => x.id === a.id);
    if (TECLAS_MAPA.includes(e.key)) {
      e.preventDefault();
      const novo = moverNoMapa(i, itens.length, e.key as TeclaMapa);
      if (novo >= 0 && novo !== i) focarItem(itens[novo]);
      return;
    }
    if (e.key.length === 1 && e.key.trim()) {
      const agora = performance.now();
      const d = digitado.current;
      d.texto = agora - d.t > 500 ? e.key : d.texto + e.key;
      d.t = agora;
      const novo = buscarNoMapa(nomesItens, i, d.texto);
      if (novo >= 0 && novo !== i) focarItem(itens[novo]);
    }
  };
  const aoFocar = (e: React.FocusEvent<SVGSVGElement>) => {
    const a = alvoDoElemento(e.target);
    if (!a) return;
    setDaVez((s) => (mesmo(s, a) ? s : a));
    // Só o foco de teclado seleciona; o toque também foca o desenho e deixava um contorno solto.
    if (!(e.target as Element).matches?.(":focus-visible")) return;
    setComFoco(a);
    if (!mesmo(sel, a)) selecionar(a);
  };
  const aoDesfocar = (e: React.FocusEvent<SVGSVGElement>) => {
    const para = e.relatedTarget as Node | null;
    if (!para || !svgRef.current?.contains(para)) setComFoco(null);
  };

  // ---- desenho ----
  const carregando = !!ufEf && !munPronto && !erro;
  const noEstado = !!ufEf;
  const naCidade = !!munEf;
  const ehSel = (nivel: NivelMapa, id: string) => sel?.nivel === nivel && sel.id === id;
  const ehSobre = (nivel: NivelMapa, id: string) => sobre?.nivel === nivel && sobre.id === id;

  const cls = [
    estilos.mapa,
    noEstado && estilos.noEstado,
    naCidade && estilos.naCidade,
    carregando && estilos.carregando,
  ]
    .filter(Boolean)
    .join(" ");

  if (erro && !ufs) {
    return (
      <p className="text-sm text-muted-foreground">
        Não foi possível carregar o mapa agora. Tente de novo em instantes.
      </p>
    );
  }

  const df = ufs?.DF;

  // Contornos de destaque numa camada por cima: no mesmo grupo os vizinhos cobriam metade do traço.
  const contornos: Array<{ chave: string; d: string; classe: string; halo: boolean }> = [];
  const dMun = (cod: string) => (detalhe?.id === cod ? detalhe.d : munPronto?.geo[cod]?.d);
  const poe = (nivel: NivelMapa, id: string, classe: string, halo = false) => {
    if (contornos.some((c) => c.chave === `${nivel}-${id}`)) return;
    if (nivel === "uf") {
      if (noEstado || !ufs?.[id]) return;
      contornos.push({ chave: `${nivel}-${id}`, d: ufs[id].d, classe, halo });
    } else {
      if (!munPronto || (naCidade && id !== munEf)) return;
      const d = dMun(id);
      if (d) contornos.push({ chave: `${nivel}-${id}`, d, classe, halo });
    }
  };
  // Foco de teclado primeiro: o contorno dele (mais grosso, sobre um halo) vence os outros.
  if (comFoco) poe(comFoco.nivel, comFoco.id, estilos.contornoFoco, true);
  if (uf) poe("uf", uf, estilos.contornoFixo);
  if (munEf) poe("mun", munEf, estilos.contornoFixo);
  if (sel) poe(sel.nivel, sel.id, estilos.contornoFixo);
  if (sobre) poe(sobre.nivel, sobre.id, estilos.contornoSobre);
  return (
    <div ref={caixaRef} className={`${estilos.caixa} ${className ?? ""}`}>
      <svg
        ref={svgRef}
        className={cls}
        viewBox={CAIXA_BRASIL.join(" ")}
        preserveAspectRatio="xMidYMid meet"
        role="group"
        aria-label={titulo}
        aria-describedby={idInstrucao}
        // No Brasil o mapa não tem gesto próprio: a página rola e amplia por cima dele. Dentro do
        // estado um dedo arrasta e dois aproximam o mapa, salvo com a página já ampliada.
        style={{ touchAction: !noEstado ? "manipulation" : ampliada ? "pan-x pan-y pinch-zoom" : "none" }}
        onPointerDown={aoApertar}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
        onPointerCancel={aoSoltar}
        onPointerLeave={aoSair}
        onClick={aoClicar}
        onKeyDown={aoTeclar}
        onFocus={aoFocar}
        onBlur={aoDesfocar}
      >
        <g>
          {ufs &&
            siglas.map((s) => (
              <Caminho
                key={s}
                d={ufs[s].d}
                nivel="uf"
                id={s}
                c={classe("uf", s)}
                rotulo={rotulo("uf", s)}
                ativa={s === uf}
                sel={ehSel("uf", s)}
                sobre={ehSobre("uf", s)}
                oculto={noEstado}
                daVez={!noEstado && s === idDaVez}
              />
            ))}
          {/* DF é minúsculo: anel de toque invisível em volta */}
          {df && (
            <circle
              className={estilos.alvo}
              cx={(df.bbox[0] + df.bbox[2]) / 2}
              cy={(df.bbox[1] + df.bbox[3]) / 2}
              r={16}
              data-id="DF"
              data-nivel="uf"
            />
          )}
        </g>
        <g>
          {munPronto &&
            Object.entries(munPronto.geo).map(([cod, m]) => (
              <Caminho
                key={cod}
                d={detalhe?.id === cod ? detalhe.d : m.d}
                nivel="mun"
                id={cod}
                c={classe("mun", cod)}
                rotulo={rotulo("mun", cod)}
                ativa={cod === munEf}
                sel={ehSel("mun", cod)}
                sobre={ehSobre("mun", cod)}
                oculto={naCidade && cod !== munEf}
                daVez={noEstado && cod === idDaVez}
              />
            ))}
        </g>
        <g aria-hidden="true" className={estilos.contornos}>
          {contornos.map((c) =>
            c.halo ? (
              <g key={c.chave}>
                <path d={c.d} className={estilos.contornoHalo} />
                <path d={c.d} className={c.classe} />
              </g>
            ) : (
              <path key={c.chave} d={c.d} className={c.classe} />
            ),
          )}
        </g>
      </svg>
      <svg ref={rotulosRef} className={estilos.rotulos} aria-hidden="true" />
      <div ref={dicaRef} className={estilos.dica} role="tooltip" hidden={!dica || !resumo}>
        {dica && resumo ? resumo(dica.nivel, dica.id) : null}
      </div>
      <p id={idInstrucao} hidden>
        Use as setas para percorrer, Enter para abrir e Esc para voltar.
      </p>
      {/* Sempre montado: o leitor só anuncia mudanças numa região que já existia. */}
      <p role="status" className="sr-only">
        {comFoco ? rotulo(comFoco.nivel, comFoco.id) : ""}
      </p>
    </div>
  );
}
