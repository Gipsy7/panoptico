"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { ExemploCard } from "@/components/exemplo-comparacao";
import { useCidadeAchada } from "@/components/localizacao-home";
import { type Comparacao, type ParlamentarResumo, getComparacao, getRepresentantes } from "@/lib/api";
import { type CasaExemplo, sortearCasa, sortearDupla, sortearItem } from "@/lib/exemplo";
import { UFS } from "@/lib/ufs";

type Exemplo = { uf: string; casa: CasaExemplo; a: ParlamentarResumo; b: ParlamentarResumo; comparacao: Comparacao };

// Altura reservada para o card não pular quando a dupla chega (o card tem cerca de 33 rem).
const RESERVA = "min-h-[34rem]";

/**
 * Exemplo de comparação: uma dupla sorteada a cada visita, no navegador e depois da hidratação
 * (sortear no servidor congelaria a mesma dupla no cache). Sorteia a Casa e o estado, e dois
 * parlamentares em exercício daquela Casa e estado. Com a cidade da pessoa achada, usa o estado
 * dela. Só a sigla do estado vai à API.
 */
export function ExemploRegional() {
  const { cidade } = useCidadeAchada();
  const ufDaPessoa = cidade?.uf ?? null;
  const [exemplo, setExemplo] = useState<Exemplo | null>(null);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    let cancelado = false;
    const uf = ufDaPessoa ?? sortearItem(UFS)!.sigla;
    const casa = sortearCasa();
    (async () => {
      const r = await getRepresentantes({ uf });
      if (!r.ok) throw new Error("representantes");
      const dupla = sortearDupla(casa === "senado" ? r.dados.senadores : r.dados.deputados);
      if (!dupla) throw new Error("sem dupla");
      const [a, b] = dupla;
      const c = await getComparacao(String(a.id), String(b.id));
      if (!c.ok || !c.dados.numeros_a || !c.dados.numeros_b) throw new Error("comparacao");
      if (!cancelado) setExemplo({ uf, casa, a, b, comparacao: c.dados });
    })().catch(() => {
      if (!cancelado) setFalhou(true);
    });
    return () => {
      cancelado = true;
    };
  }, [ufDaPessoa]);

  return (
    <div className={RESERVA}>
      {exemplo ? (
        <div key={`${exemplo.uf}-${exemplo.a.id}-${exemplo.b.id}`} className="troca-suave">
          <ExemploCard uf={exemplo.uf} casa={exemplo.casa} a={exemplo.a} b={exemplo.b} comparacao={exemplo.comparacao} />
        </div>
      ) : (
        <div className="flex flex-col gap-4 border border-border p-[var(--esp-4)]">
          {falhou ? (
            <p className="text-sm text-muted-foreground">Não deu para montar o exemplo agora.</p>
          ) : (
            <EsqueletoSecao rotulo="Carregando o exemplo de comparação…" linhas={6} secoes={2} />
          )}
          <Link href="/comparar" className="botao-linha self-start">
            Comparar parlamentares
          </Link>
        </div>
      )}
    </div>
  );
}
