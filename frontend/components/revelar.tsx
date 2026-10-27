"use client";

import { useEffect, useState } from "react";

// Revelar proporcional à rolagem: cada `.revelar-item` (e cada `.revelar` sem itens dentro) recebe
// `--p` de 0 a 1 conforme o topo sobe de 100% a 65% da altura da janela; o CSS deriva dele a
// opacidade e o deslocamento. Ao chegar a 1 vira `.rv-ok` e sai da lista (nunca volta a esconder).
// O CSS só esconde com `html.js-revelar` e sem redução de movimento; sem JS tudo aparece.
// Um MutationObserver pega o que chega depois (Suspense, navegação entre rotas).
const ALVOS = ".revelar-item, .revelar:not(:has(.revelar-item))";
const FIM = 0.35; // fração da janela percorrida entre --p 0 e --p 1

export function Revelar() {
  useEffect(() => {
    const raiz = document.documentElement;
    const vistos = new WeakSet<Element>();
    const ativos = new Set<HTMLElement>();
    let quadro = 0;

    const concluir = (el: HTMLElement) => {
      el.style.setProperty("--p", "1");
      el.classList.add("rv-ok");
      ativos.delete(el);
      io.unobserve(el);
    };

    const atualizar = () => {
      quadro = 0;
      const altura = window.innerHeight;
      ativos.forEach((el) => {
        const t = (altura - el.getBoundingClientRect().top) / (altura * FIM);
        if (t >= 1) concluir(el);
        else el.style.setProperty("--p", (1 - (1 - Math.max(t, 0)) ** 2).toFixed(3));
      });
    };
    const agendar = () => {
      if (!quadro) quadro = requestAnimationFrame(atualizar);
    };

    // Só os elementos perto da janela ficam na lista de ativos.
    const io = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        const el = e.target as HTMLElement;
        if (e.isIntersecting) ativos.add(el);
        else {
          ativos.delete(el);
          // Passou direto (salto de âncora, rolagem rápida): fica revelado.
          if (e.boundingClientRect.bottom <= 0) concluir(el);
        }
      }
      agendar();
    });

    const varrer = () => {
      const altura = window.innerHeight;
      document.querySelectorAll<HTMLElement>(ALVOS).forEach((el) => {
        if (vistos.has(el)) return;
        vistos.add(el);
        // Já na tela ao carregar: entra com --p 1, sem piscar.
        if (el.getBoundingClientRect().top < altura * 0.9) {
          el.style.setProperty("--p", "1");
          el.classList.add("rv-ok");
        } else {
          el.style.setProperty("--p", "0");
          io.observe(el);
        }
      });
    };

    varrer();
    raiz.classList.add("js-revelar");
    window.addEventListener("scroll", agendar, { passive: true });
    window.addEventListener("resize", agendar);

    let quadroMut = 0;
    const mo = new MutationObserver(() => {
      cancelAnimationFrame(quadroMut);
      quadroMut = requestAnimationFrame(varrer);
    });
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      mo.disconnect();
      io.disconnect();
      window.removeEventListener("scroll", agendar);
      window.removeEventListener("resize", agendar);
      cancelAnimationFrame(quadro);
      cancelAnimationFrame(quadroMut);
      raiz.classList.remove("js-revelar");
    };
  }, []);

  return null;
}

// Dica discreta no pé do primeiro bloco (só no computador); some depois que a pessoa rola.
export function IndicadorRolagem() {
  const [rolou, setRolou] = useState(false);

  useEffect(() => {
    const aoRolar = () => setRolou(window.scrollY > 40);
    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);

  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-x-0 bottom-2 hidden flex-col items-center gap-1 text-sm text-muted-foreground transition-opacity duration-500 md:flex ${rolou ? "opacity-0" : "opacity-100"}`}
    >
      <span>Role para ver mais</span>
      <svg viewBox="0 0 24 24" className="size-5 animate-bounce motion-reduce:animate-none" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>
  );
}
