"use client";

import { useRouter } from "next/navigation";

import { Cadeiras } from "@/components/casa/cadeiras";
import type { ComposicaoCongresso } from "@/lib/api";

const NOME = { camara: "Câmara dos Deputados", senado: "Senado Federal" } as const;

/**
 * Cadeiras do Congresso no topo de /parlamentares. Tocar num partido troca o filtro de partido
 * da lista (o mesmo parâmetro `partido` da URL); tocar de novo tira o filtro. `endereco(partido)`
 * vem da página, que sabe montar a URL com os demais filtros.
 */
export function CadeirasCongresso({
  composicao,
  partidoAtivo,
  enderecos,
}: {
  composicao: ComposicaoCongresso;
  partidoAtivo: string | null;
  /** URL da lista para cada partido da composição de hoje, e a sem partido (chave ""). */
  enderecos: Record<string, string>;
}) {
  const roteador = useRouter();
  const c = composicao;
  return (
    <Cadeiras
      titulo={`Cadeiras: ${NOME[c.casa]}`}
      nivelTitulo={2}
      nome={NOME[c.casa]}
      hoje={c.hoje}
      depois={c.a_partir_2027}
      fonte={{ nome: c.fonte_nome, url: c.fonte_url, atualizadoEm: c.atualizado_em }}
      fonteDepois={
        c.a_partir_2027 && c.fonte_2027_nome
          ? { nome: c.fonte_2027_nome, url: c.fonte_2027_url ?? undefined, atualizadoEm: c.atualizado_2027_em }
          : null
      }
      escolhido={partidoAtivo}
      onEscolher={(partido) => {
        const destino = enderecos[partido ?? ""];
        if (destino) roteador.push(destino, { scroll: false });
      }}
    />
  );
}
