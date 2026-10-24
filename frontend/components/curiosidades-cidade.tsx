"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { useCidadeAchada } from "@/components/localizacao-home";
import { getCamara, getContas, getDinheiroFederalMunicipio, getEmendasMunicipio } from "@/lib/api";
import { type Curiosidade, escolherCuriosidades, sortearCuriosidade } from "@/lib/curiosidades";

// Último ano fechado dos repasses federais (o mesmo da página da cidade).
const ANO_LIMITE_REPASSES = 2025;

type Pronto = { ibge: string; item: Curiosidade | null };

/**
 * Depois que a cidade é achada, mostra UM número dela, sorteado entre os disponíveis, numa frase
 * discreta com a média das cidades do estado quando existe, o link da página e a fonte. As buscas usam só o código IBGE da cidade, em
 * paralelo, e só começam depois que o aparelho achou a cidade.
 */
export function CuriosidadesCidade() {
  const { cidade } = useCidadeAchada();
  const ibge = cidade?.ibge ?? null;
  const nome = cidade?.nome ?? "";
  const uf = cidade?.uf ?? "";
  const [pronto, setPronto] = useState<Pronto | null>(null);

  useEffect(() => {
    if (!ibge) return;
    let cancelado = false;
    Promise.all([
      getDinheiroFederalMunicipio(ibge),
      getContas(ibge),
      getEmendasMunicipio(ibge),
      getCamara(ibge),
    ])
      .then(([federal, contas, emendas, camara]) => {
        if (cancelado) return;
        const itens = escolherCuriosidades({
          cidade: { nome, uf, ibge },
          federal: federal.ok ? federal.dados : null,
          contas: contas.ok ? contas.dados : null,
          emendas: emendas.ok ? emendas.dados : null,
          camara: camara.ok ? camara.dados : null,
          anoLimiteRepasses: ANO_LIMITE_REPASSES,
        });
        setPronto({ ibge, item: sortearCuriosidade(itens) });
      })
      .catch(() => {});
    return () => {
      cancelado = true;
    };
  }, [ibge, nome, uf]);

  const c = pronto && pronto.ibge === ibge ? pronto.item : null;

  return (
    <div aria-live="polite" className="max-w-md empty:hidden">
      {c && (
        <div className="troca-suave flex flex-col gap-1 border-l-2 border-bronze pl-3">
          <p className="text-sm">
            <span className="text-muted-foreground">{c.rotulo}: </span>
            <span className="numero text-base">{c.valor}</span>
            {c.media && (
              <span className="text-muted-foreground">
                {" "}
                ({c.media.rotulo.charAt(0).toLowerCase() + c.media.rotulo.slice(1)}:{" "}
                <span className="tabular-nums">{c.media.valor}</span>)
              </span>
            )}
            .{" "}
            <Link href={c.href} className="inline-flex min-h-11 items-center font-medium underline underline-offset-4">
              Ver mais
            </Link>
          </p>
          <FonteRodape fonte={c.fonte.nome} url={c.fonte.url} atualizadoEm={c.fonte.atualizadoEm} />
        </div>
      )}
    </div>
  );
}
