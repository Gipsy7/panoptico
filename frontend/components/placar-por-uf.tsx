/**
 * Placar por estado: quantos votaram Sim, Não e outros registros em cada UF. Com um estado
 * escolhido, a linha dele vem em destaque; a lista dos demais abre num <details>.
 */
import { BarraPlacar } from "@/components/barra-placar";
import type { PorUf } from "@/lib/api";
import { UFS } from "@/lib/ufs";

const nomeUf = (sigla: string) => UFS.find((u) => u.sigla === sigla)?.nome ?? sigla;

function Linha({ x }: { x: PorUf }) {
  return (
    <li className="flex flex-col gap-1 py-2">
      <p className="flex items-baseline justify-between gap-3">
        <span className="font-medium">{nomeUf(x.uf)}</span>
        <span className="text-sm text-muted-foreground tabular-nums">
          {x.sim} Sim · {x.nao} Não{x.outros > 0 ? ` · ${x.outros} outros` : ""}
        </span>
      </p>
      <BarraPlacar sim={x.sim} nao={x.nao} />
    </li>
  );
}

export function PlacarPorUf({ porUf, uf }: { porUf: PorUf[]; uf: string | null }) {
  if (porUf.length === 0) return null;
  const escolhido = uf ? porUf.find((x) => x.uf === uf) : null;
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-base font-semibold">Placar por estado</h4>
      {uf && !escolhido && (
        <p className="text-sm text-muted-foreground">Ninguém de {nomeUf(uf)} aparece nesta votação.</p>
      )}
      {escolhido && <ul className="lista-fios">{<Linha x={escolhido} />}</ul>}
      <details className="group">
        <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
          {escolhido ? "Ver todos os estados" : "Ver o placar de cada estado"}
        </summary>
        <ul className="lista-fios">
          {porUf.map((x) => (
            <Linha key={x.uf} x={x} />
          ))}
        </ul>
      </details>
    </div>
  );
}
