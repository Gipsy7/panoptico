"use client";

/**
 * O calendário de votações sem recarregar a página: tocar num dia, num mês, numa Casa ou na chave
 * "Só o que muda leis" busca só os dados do calendário (GET /votacoes/calendario, ~0,4 s) e troca o
 * endereço com `history.replaceState`, sem refazer a lista de projetos (~1 s, e o esqueleto de
 * carregamento que fazia a página pular). Os links continuam de verdade: sem JavaScript, ou com
 * Ctrl/Cmd, abrem o endereço como antes; se a busca falhar, também.
 */
import { useRef, useState } from "react";

import { CalendarioVotacoes } from "@/components/calendario-votacoes";
import { type CalendarioVotacoes as Dados, getCalendarioVotacoes } from "@/lib/api";
import { type EstadoCalendario, lerCalendario } from "@/lib/calendario-votacoes";

export function CalendarioAoVivo({
  dadosIniciais,
  estadoInicial,
}: {
  dadosIniciais: Dados;
  estadoInicial: EstadoCalendario;
}) {
  const [atual, setAtual] = useState({ dados: dadosIniciais, estado: estadoInicial });
  const [buscando, setBuscando] = useState(false);
  const pedido = useRef(0);

  async function ir(href: string) {
    const url = new URL(href, window.location.href);
    const estado = lerCalendario(Object.fromEntries(url.searchParams));
    const [ano, mes] = estado.mes ? estado.mes.split("-") : [undefined, undefined];
    const n = ++pedido.current;
    setBuscando(true);
    const r = await getCalendarioVotacoes({
      casa: estado.casa,
      ano,
      mes,
      dia: estado.dia,
      tipo: estado.tipo,
      pagina: estado.pagina,
    });
    if (n !== pedido.current) return; // outro clique chegou antes
    setBuscando(false);
    if (!r.ok) {
      window.location.assign(url.toString()); // sem a busca, vai pelo endereço como antes
      return;
    }
    setAtual({ dados: r.dados, estado });
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  }

  return (
    <div
      aria-busy={buscando || undefined}
      className={buscando ? "opacity-70 transition-opacity" : "transition-opacity"}
      onClickCapture={(e) => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        const link = (e.target as Element).closest("a[href]");
        if (!(link instanceof HTMLAnchorElement)) return;
        const url = new URL(link.href);
        if (url.origin !== window.location.origin || url.pathname !== "/projetos") return;
        e.preventDefault();
        e.stopPropagation(); // nem o Link do Next nem a chave navegam: a página fica onde está
        void ir(link.href);
      }}
      onKeyDownCapture={(e) => {
        // A chave "Só o que muda leis" também liga com a barra de espaço.
        if (e.key !== " ") return;
        const link = (e.target as Element).closest('a[role="switch"][href]');
        if (!(link instanceof HTMLAnchorElement)) return;
        e.preventDefault();
        e.stopPropagation();
        void ir(link.href);
      }}
    >
      <CalendarioVotacoes dados={atual.dados} estado={atual.estado} />
    </div>
  );
}
