"use client";

import { type PointerEvent, useEffect, useId, useRef, useState } from "react";

import { ArgosChat } from "@/components/argos/argos-chat";
import { tornarFundoInerte } from "@/lib/fundo-inerte";

/** Preferência de tela (lado e altura do botão): localStorage, não é dado pessoal. */
const CHAVE_POSICAO = "argos-posicao";
/** Botão escondido até fechar a aba. */
export const CHAVE_OCULTO = "argos-oculto";
/** Evento que traz o botão de volta (o link do rodapé e /pergunte o disparam). */
export const EVENTO_RESTAURAR = "argos:restaurar";

const MARGEM = 8;
/** Altura do cabeçalho (3,5 rem = 56 px) mais a margem: o botão nunca o cobre. */
const TOPO = 64;
/** Movimento mínimo, em px, para o gesto virar arrastar (abaixo disso é um toque). */
const LIMIAR = 6;

type Lado = "esquerda" | "direita";
type Posicao = { lado: Lado; y: number };

function limitarY(y: number, altura: number) {
  return Math.min(Math.max(y, TOPO), Math.max(TOPO, window.innerHeight - altura - MARGEM));
}

function lerPosicao(): Posicao | null {
  try {
    const bruto = JSON.parse(localStorage.getItem(CHAVE_POSICAO) ?? "null");
    if ((bruto?.lado === "esquerda" || bruto?.lado === "direita") && Number.isFinite(bruto.y)) {
      return { lado: bruto.lado, y: bruto.y };
    }
  } catch {
    // Armazenamento bloqueado ou valor estragado: usa a posição padrão.
  }
  return null;
}

function Olho({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/**
 * Botão do Argos em todas as telas (escondido em /pergunte por CSS: a página marca o <html> com
 * `data-argos-pagina`). Dá para arrastá-lo (toque ou mouse): ao soltar, encaixa na borda esquerda
 * ou direita mais próxima e nunca sai da tela nem cobre o cabeçalho. Um "×" o esconde até fechar
 * a aba. No celular só o olho; no computador, o olho e o texto. Abre o chat por cima: tela cheia
 * no celular, painel lateral no computador. O chat só é carregado na primeira abertura e, depois,
 * fica na memória (fechado) para a conversa continuar ao mudar de página. Esc fecha e o foco
 * volta ao botão.
 */
export function ArgosBotao() {
  const idTitulo = useId();
  const [aberto, setAberto] = useState(false);
  const [jaAbriu, setJaAbriu] = useState(false);
  const [oculto, setOculto] = useState(false);
  const [posicao, setPosicao] = useState<Posicao | null>(null);
  const [arrastando, setArrastando] = useState<{ x: number; y: number } | null>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const caixa = useRef<HTMLDivElement>(null);
  const painel = useRef<HTMLDivElement>(null);
  const devolverFoco = useRef(false);
  const gesto = useRef<{ id: number; x: number; y: number; esquerda: number; topo: number; moveu: boolean } | null>(null);
  const ignorarClique = useRef(false);

  function abrir() {
    setJaAbriu(true);
    setAberto(true);
  }

  function fechar(comFoco: boolean) {
    devolverFoco.current = comFoco;
    setAberto(false);
  }

  function esconder() {
    try {
      sessionStorage.setItem(CHAVE_OCULTO, "1");
    } catch {
      // Sem armazenamento da aba: esconde só nesta página.
    }
    setOculto(true);
  }

  // Preferências guardadas e pedido de volta.
  useEffect(() => {
    // Só pode ler o armazenamento depois da hidratação (o servidor não o tem).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPosicao(lerPosicao());
    try {
      setOculto(sessionStorage.getItem(CHAVE_OCULTO) === "1");
    } catch {
      // Sem armazenamento da aba: o botão fica visível.
    }
    const voltar = () => setOculto(false);
    window.addEventListener(EVENTO_RESTAURAR, voltar);
    return () => window.removeEventListener(EVENTO_RESTAURAR, voltar);
  }, []);

  // Girar o celular ou redimensionar: mantém o botão dentro da tela.
  useEffect(() => {
    const ajustar = () => {
      const altura = caixa.current?.offsetHeight ?? 44;
      setPosicao((p) => (p ? { ...p, y: limitarY(p.y, altura) } : p));
    };
    window.addEventListener("resize", ajustar);
    window.addEventListener("orientationchange", ajustar);
    return () => {
      window.removeEventListener("resize", ajustar);
      window.removeEventListener("orientationchange", ajustar);
    };
  }, []);

  function aoPressionar(e: PointerEvent<HTMLButtonElement>) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    const r = caixa.current?.getBoundingClientRect();
    if (!r) return;
    gesto.current = { id: e.pointerId, x: e.clientX, y: e.clientY, esquerda: r.left, topo: r.top, moveu: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function aoMover(e: PointerEvent<HTMLButtonElement>) {
    const g = gesto.current;
    const c = caixa.current;
    if (!g || g.id !== e.pointerId || !c) return;
    const dx = e.clientX - g.x;
    const dy = e.clientY - g.y;
    if (!g.moveu && Math.hypot(dx, dy) < LIMIAR) return;
    g.moveu = true;
    setArrastando({
      x: Math.min(Math.max(g.esquerda + dx, 0), window.innerWidth - c.offsetWidth),
      y: limitarY(g.topo + dy, c.offsetHeight),
    });
  }

  function aoSoltar(e: PointerEvent<HTMLButtonElement>) {
    const g = gesto.current;
    const c = caixa.current;
    gesto.current = null;
    if (!g || g.id !== e.pointerId || !c) return;
    if (!g.moveu) return; // toque curto: o clique abre
    ignorarClique.current = true;
    setTimeout(() => (ignorarClique.current = false), 0);
    const dx = e.clientX - g.x;
    const dy = e.clientY - g.y;
    const centro = Math.min(Math.max(g.esquerda + dx, 0), window.innerWidth - c.offsetWidth) + c.offsetWidth / 2;
    const nova: Posicao = {
      lado: centro < window.innerWidth / 2 ? "esquerda" : "direita",
      y: limitarY(g.topo + dy, c.offsetHeight),
    };
    setArrastando(null);
    setPosicao(nova);
    try {
      localStorage.setItem(CHAVE_POSICAO, JSON.stringify(nova));
    } catch {
      // Sem armazenamento: vale até recarregar.
    }
  }

  function aoCancelar() {
    gesto.current = null;
    setArrastando(null);
  }

  function aoClicar() {
    if (ignorarClique.current) return;
    abrir();
  }

  // Aberto: trava a rolagem do fundo, deixa o resto da página inerte (o TalkBack ignora
  // aria-modal), foca o painel e fecha com Esc.
  useEffect(() => {
    if (!aberto) {
      if (devolverFoco.current) botao.current?.focus();
      devolverFoco.current = false;
      return;
    }
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        devolverFoco.current = true;
        setAberto(false);
      }
    };
    document.addEventListener("keydown", aoTeclar);
    const desfazerInerte = painel.current ? tornarFundoInerte(painel.current) : () => {};
    painel.current?.focus();
    return () => {
      desfazerInerte();
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  const estilo = arrastando
    ? { left: arrastando.x, top: arrastando.y, right: "auto", bottom: "auto" }
    : posicao
      ? {
          top: posicao.y,
          bottom: "auto",
          ...(posicao.lado === "direita" ? { right: MARGEM, left: "auto" } : { left: MARGEM, right: "auto" }),
        }
      : undefined;
  const invertido = (arrastando ? false : posicao?.lado === "esquerda") ? "flex-row-reverse" : "flex-row";

  return (
    <>
      {!oculto && (
        <div
          ref={caixa}
          style={estilo}
          className={`argos-botao fixed z-30 flex items-center ${invertido} print:hidden ${posicao || arrastando ? "" : "right-2 bottom-4"}`}
        >
          <button
            type="button"
            onClick={esconder}
            aria-label="Esconder o Argos"
            className="flex size-11 shrink-0 items-center justify-center focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-bronze-texto"
          >
            <span className="flex size-6 items-center justify-center rounded-[2px] bg-secondary text-foreground ring-1 ring-foreground/25">
              <svg aria-hidden viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </span>
          </button>
          <button
            ref={botao}
            type="button"
            aria-label="Pergunte ao Argos"
            aria-haspopup="dialog"
            onClick={aoClicar}
            onPointerDown={aoPressionar}
            onPointerMove={aoMover}
            onPointerUp={aoSoltar}
            onPointerCancel={aoCancelar}
            className="inline-flex size-11 shrink-0 cursor-grab touch-none items-center justify-center gap-2 rounded-[2px] bg-foreground text-sm font-medium text-background select-none hover:bg-foreground/85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze active:cursor-grabbing sm:w-auto sm:px-4"
          >
            <Olho className="size-5 shrink-0" />
            <span className="hidden sm:inline">Pergunte ao Argos</span>
          </button>
        </div>
      )}

      {jaAbriu && (
        <div
          ref={painel}
          role="dialog"
          aria-modal="true"
          aria-labelledby={idTitulo}
          tabIndex={-1}
          className={`argos-painel fixed inset-0 z-50 flex-col gap-3 bg-background p-4 outline-none md:inset-y-0 md:right-0 md:left-auto md:w-[min(28rem,100vw)] md:border-l md:border-border ${aberto ? "flex" : "hidden"}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 id={idTitulo} className="flex items-center gap-2 text-2xl">
                <Olho className="size-6 shrink-0 text-bronze-texto" />
                Argos
              </h2>
              <p className="text-sm text-muted-foreground">
                Respostas com os dados oficiais do site. Não dou opinião nem nota.
              </p>
            </div>
            <button type="button" onClick={() => fechar(true)} className="botao-linha shrink-0 px-3">
              Fechar
              <span className="sr-only"> o chat com o Argos</span>
            </button>
          </div>
          <ArgosChat modo="painel" aoNavegar={() => fechar(false)} />
        </div>
      )}
    </>
  );
}
