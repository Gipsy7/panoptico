"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLugar } from "@/components/lugar-escolhido";
import { Foto } from "@/components/parlamentar-card";
import { type ParlamentarResumo, getCamara, getMaisVotados, getRepresentantes } from "@/lib/api";
import {
  ANO_ELEICAO_FEDERAL,
  enderecoComparar,
  listaDeNomes,
  maisVotadosEmExercicio,
  mesmoGrupo,
  senadoresDoEstado,
} from "@/lib/comparar-sugestoes";

type Atalho = {
  id: "senadores" | "votados" | "vereadores";
  titulo: string;
  /** Nome curto, para as abas dentro do resultado. */
  curto: string;
  detalhe: string;
  href: string;
  ids: number[] | null;
  pessoas: ParlamentarResumo[];
};

/**
 * Atalhos do comparador a partir do lugar guardado no aparelho: os senadores do estado, os dois
 * deputados federais eleitos mais votados na cidade e os vereadores da câmara. Tudo no navegador
 * (o lugar só existe nele); à API vão só o código da cidade e, por ela, o estado.
 *
 * `idsAtuais` liga o modo compacto: uma linha de abas acima do resultado, para trocar de grupo
 * sem voltar à página vazia.
 */
export function CompararSugestoes({ idsAtuais }: { idsAtuais?: number[] }) {
  const lugar = useLugar();
  const [atalhos, setAtalhos] = useState<Atalho[] | null>(null);
  const compacto = idsAtuais !== undefined;

  useEffect(() => {
    if (!lugar) return;
    let cancelado = false;
    (async () => {
      const [rep, votados, camara] = await Promise.all([
        getRepresentantes({ municipio: lugar.ibge }),
        getMaisVotados(lugar.ibge, ANO_ELEICAO_FEDERAL),
        getCamara(lugar.ibge),
      ]);
      const lista: Atalho[] = [];
      if (rep.ok) {
        const senadores = senadoresDoEstado(rep.dados.senadores);
        if (senadores) {
          const ids = senadores.map((s) => s.id);
          lista.push({
            id: "senadores",
            titulo: `Os ${senadores.length} senadores de ${lugar.uf}`,
            curto: `Senadores de ${lugar.uf}`,
            detalhe: listaDeNomes(senadores.map((s) => s.nome_parlamentar)),
            href: enderecoComparar(ids),
            ids,
            pessoas: senadores,
          });
        }
        const federais =
          votados.ok && votados.dados.ano === ANO_ELEICAO_FEDERAL
            ? (votados.dados.cargos.find((c) => c.cargo.toUpperCase() === "DEPUTADO FEDERAL")?.itens ?? [])
            : [];
        const dupla = maisVotadosEmExercicio(federais, rep.dados.deputados);
        if (dupla) {
          const ids = dupla.map((d) => d.id);
          lista.push({
            id: "votados",
            titulo: `Os 2 deputados federais mais votados em ${lugar.nome}`,
            curto: `Mais votados em ${lugar.nome}`,
            detalhe: `${listaDeNomes(dupla.map((d) => d.nome_parlamentar))}, eleitos em ${ANO_ELEICAO_FEDERAL}`,
            href: enderecoComparar(ids),
            ids,
            pessoas: dupla,
          });
        }
      }
      if (camara.ok && camara.dados.itens.length >= 2) {
        lista.push({
          id: "vereadores",
          titulo: `Vereadores de ${lugar.nome}`,
          curto: "Vereadores",
          detalhe: `Escolha de 2 a 4 entre os ${camara.dados.itens.length}`,
          href: `/comparar/local?ibge=${lugar.ibge}`,
          ids: null,
          pessoas: [],
        });
      }
      if (!cancelado) setAtalhos(lista);
    })().catch(() => {
      if (!cancelado) setAtalhos([]);
    });
    return () => {
      cancelado = true;
    };
  }, [lugar]);

  if (compacto) {
    // Dentro do resultado: sem lugar ou sem atalho, não aparece nada.
    if (!lugar || !atalhos || atalhos.length === 0) return null;
    return (
      <nav aria-label={`Outras comparações de ${lugar.nome}`} className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">De {lugar.nome}:</span>
        {atalhos.map((a) => {
          const atual = a.ids !== null && mesmoGrupo(a.ids, idsAtuais);
          return (
            <Link
              key={a.id}
              href={a.href}
              aria-current={atual ? "page" : undefined}
              className={`inline-flex min-h-11 items-center border px-3 ${
                atual ? "border-foreground font-semibold" : "border-border hover:border-foreground"
              }`}
            >
              {a.curto}
            </Link>
          );
        })}
      </nav>
    );
  }

  if (!lugar) {
    return (
      <p className="text-sm text-muted-foreground">
        Com a sua cidade escolhida, aparecem aqui comparações prontas de quem representa você.{" "}
        <Link href="/#cep" className="underline underline-offset-2">
          Escolher a cidade
        </Link>
      </p>
    );
  }
  if (atalhos === null) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        Buscando quem representa {lugar.nome}…
      </p>
    );
  }
  if (atalhos.length === 0) return null;

  return (
    <section aria-labelledby="atalhos-titulo" className="flex flex-col gap-3">
      <h2 id="atalhos-titulo" className="font-sans text-base font-semibold tracking-normal">
        Comece por quem representa {lugar.nome}
      </h2>
      <ul className="flex flex-col gap-2">
        {atalhos.map((a) => (
          <li key={a.id}>
            <Link
              href={a.href}
              className="flex min-h-14 items-center gap-3 border border-border bg-card px-3 py-2 hover:border-foreground"
            >
              {a.pessoas.length > 0 && (
                <span aria-hidden className="flex shrink-0 -space-x-2">
                  {a.pessoas.map((p) => (
                    <span key={p.id} className="overflow-hidden rounded-full ring-2 ring-card">
                      <Foto parlamentar={p} largura={30} decorativa />
                    </span>
                  ))}
                </span>
              )}
              <span className="flex min-w-0 flex-col">
                <span className="font-semibold">{a.titulo}</span>
                <span className="text-sm text-muted-foreground">{a.detalhe}</span>
              </span>
              <span aria-hidden className="ml-auto text-xl text-bronze-texto">
                ›
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        Os senadores são todos os do estado, em ordem alfabética. Os deputados são os dois eleitos com mais votos na
        cidade em {ANO_ELEICAO_FEDERAL} (TSE). Não é uma seleção do site.
      </p>
    </section>
  );
}
