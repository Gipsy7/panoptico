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
  useState,
  type ReactNode,
  type Ref,
} from "react";
import {
  CAIXA_BRASIL,
  carregarDetalhe,
  carregarMunicipios,
  carregarUfs,
  type Caixa,
  type ClasseMapa,
  type Lugar,
  type MalhaMun,
  type MalhaUf,
  type NivelMapa,
} from "@/lib/mapa";
import estilos from "./mapa-brasil.module.css";

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
  tabIndex: number;
}

const Caminho = memo(function Caminho({ d, nivel, id, c, rotulo, ativa, sel, sobre, tabIndex }: CaminhoProps) {
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
      tabIndex={tabIndex}
      role="button"
      aria-label={rotulo}
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
}: MapaBrasilProps) {
  const [ufs, setUfs] = useState<MalhaUf | null>(null);
  const [muns, setMuns] = useState<{ uf: string; geo: MalhaMun } | null>(null);
  const [detalhe, setDetalhe] = useState<{ id: string; d: string } | null>(null);
  const [erro, setErro] = useState(false);
  const [sobre, setSobre] = useState<Alvo | null>(null);
  const [dica, setDica] = useState<Alvo | null>(null);
  const [sel, setSel] = useState<Alvo | null>(null);

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
  const inicio = useRef<{ x: number; y: number; vb: Vb; d: number | null; cx: number; cy: number }>({
    x: 0,
    y: 0,
    vb: [...CAIXA_BRASIL],
    d: null,
    cx: 0,
    cy: 0,
  });
  // Valores atuais para handlers nativos e callbacks estáveis.
  const atual = useRef({ ufEf, munEf, ufs, muns, onNavegar, onSelecionar });
  useEffect(() => {
    atual.current = { ufEf, munEf, ufs, muns, onNavegar, onSelecionar };
  });

  const setVB = useCallback((v: Vb) => {
    vb.current = v;
    svgRef.current?.setAttribute("viewBox", v.map((x) => x.toFixed(2)).join(" "));
  }, []);

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
    const aoRedimensionar = () => {
      if (!arrastando.current) setVB(enquadrar());
    };
    addEventListener("resize", aoRedimensionar);
    return () => removeEventListener("resize", aoRedimensionar);
  }, [enquadrar, setVB]);

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
      const w = Math.min(lim[2], Math.max(lim[2] / 25, w0 / fator));
      const k = w / w0;
      anim.current++;
      setVB([px - (px - x) * k, py - (py - y) * k, w, h0 * k]);
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
    svg.addEventListener("wheel", roda, { passive: false });
    return () => svg.removeEventListener("wheel", roda);
  }, [zoomEm, ufs]);

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
    if (ponteiros.current.size === 2 && ini.d) {
      const [a, b] = [...ponteiros.current.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      arrastando.current = true;
      const f = d / ini.d;
      ini.d = d;
      zoomEm(ini.cx, ini.cy, f);
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
    inicio.current = { x: e.clientX, y: e.clientY, vb: [...vb.current], d: null, cx: 0, cy: 0 };
    arrastando.current = false;
    if (ponteiros.current.size === 2) {
      const [a, b] = [...ponteiros.current.values()];
      inicio.current.d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      inicio.current.cx = (a[0] + b[0]) / 2;
      inicio.current.cy = (a[1] + b[1]) / 2;
    }
  };
  const aoSoltar = (e: React.PointerEvent<SVGSVGElement>) => {
    const era = arrastando.current;
    ponteiros.current.delete(e.pointerId);
    if (ponteiros.current.size) return;
    arrastando.current = false;
    if (e.type === "pointerup" && !era) tocar(alvoDe(e), e.pointerType);
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
  const aoTeclar = (e: React.KeyboardEvent<SVGSVGElement>) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const a = alvoDoElemento(e.target);
    if (!a) return;
    e.preventDefault();
    ativar(a);
  };
  const aoFocar = (e: React.FocusEvent<SVGSVGElement>) => {
    const a = alvoDoElemento(e.target);
    if (a) selecionar(a);
  };

  // ---- desenho ----
  const carregando = !!ufEf && !munPronto && !erro;
  const noEstado = !!ufEf;
  const naCidade = !!munEf;
  const siglas = useMemo(() => (ufs ? Object.keys(ufs) : []), [ufs]);
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
  return (
    <div ref={caixaRef} className={`${estilos.caixa} ${className ?? ""}`}>
      <svg
        ref={svgRef}
        className={cls}
        viewBox={CAIXA_BRASIL.join(" ")}
        preserveAspectRatio="xMidYMid meet"
        role="group"
        aria-label={titulo}
        style={{ touchAction: noEstado ? "none" : "pan-y" }}
        onPointerDown={aoApertar}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
        onPointerCancel={aoSoltar}
        onPointerLeave={aoSair}
        onKeyDown={aoTeclar}
        onFocus={aoFocar}
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
                tabIndex={noEstado ? -1 : 0}
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
                tabIndex={naCidade && cod !== munEf ? -1 : 0}
              />
            ))}
        </g>
      </svg>
      <div ref={dicaRef} className={estilos.dica} role="tooltip" hidden={!dica || !resumo}>
        {dica && resumo ? resumo(dica.nivel, dica.id) : null}
      </div>
    </div>
  );
}
